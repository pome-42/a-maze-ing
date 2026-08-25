#!/usr/bin/env bash

set -Eeuo pipefail

# Submission policy:
# - .github is disposable even when it contains local changes and is removed first.
# - README.md must be clean before default removal; -K preserves it with local changes.
# - pyproject.toml, .gitignore, renovate.json, and this script must be clean.
# - .gitignore rules are installed into the repository-local exclude file first,
#   so ignored work files stay protected after .gitignore is deleted.
# - Linked worktrees are rejected because they share the local exclude file.

repo_root=""
script_relpath=""
head_commit=""
platform_name=""
removal_started=0
removal_completed=0
git_exclude_path=""
gitignore_import_confirmed=0
help_requested=0
keep_readme=0

managed_begin='# BEGIN prepare_submission.sh managed .gitignore rules'
managed_end='# END prepare_submission.sh managed .gitignore rules'
managed_block_malformed_status=42

must_be_clean_paths=()
always_remove_paths=()
remove_paths=()
restore_paths=()

error() {
    printf 'Error: %s\n' "$1" >&2
}

repo_git() {
    git -C "$repo_root" "$@"
}

print_usage() {
    printf 'Usage: %s [-K | --keep-readme]\n' "$(basename -- "$0")"
    printf '\nOptions:\n'
    printf '  -K, --keep-readme  Keep README.md, including local changes.\n'
    printf '  -h, --help         Show this help message.\n'
}

parse_arguments() {
    if [ "$#" -gt 1 ]; then
        error 'only one option may be specified.'
        print_usage >&2
        return 2
    fi
    if [ "$#" -eq 0 ]; then
        return 0
    fi

    case "$1" in
        -K|--keep-readme) keep_readme=1 ;;
        -h|--help) help_requested=1 ;;
        *)
            error "unknown option: $1"
            print_usage >&2
            return 2
            ;;
    esac
}

discover_repository() {
    local script_path

    if [ -L "$0" ]; then
        error 'prepare_submission.sh must not be a symbolic link.'
        return 1
    fi

    script_path="$(cd -- "$(dirname -- "$0")" && pwd -P)/$(basename -- "$0")"
    if ! repo_root="$(git -C "$(dirname -- "$script_path")" rev-parse --show-toplevel 2>/dev/null)"; then
        error 'this script must be run inside a Git repository.'
        return 1
    fi

    case "$script_path" in
        "$repo_root"/*) ;;
        *)
            error 'the script must be located inside the Git repository.'
            return 1
            ;;
    esac
    script_relpath="${script_path#"$repo_root"/}"

    head_commit="$(repo_git rev-parse HEAD)" || {
        error 'failed to identify the current Git commit.'
        return 1
    }
    if ! repo_git cat-file -e "$head_commit:$script_relpath" 2>/dev/null; then
        error 'prepare_submission.sh must be committed before running it.'
        return 1
    fi
}

configure_targets() {
    must_be_clean_paths=()
    if [ "$keep_readme" -eq 0 ]; then
        must_be_clean_paths+=("README.md")
    fi
    must_be_clean_paths+=(
        "pyproject.toml"
        ".gitignore"
        "renovate.json"
        "$script_relpath"
    )
    always_remove_paths=(
        ".github"
    )
    remove_paths=(
        "${always_remove_paths[@]}"
        "${must_be_clean_paths[@]}"
    )
}

configure_restore_paths() {
    local path

    restore_paths=()
    for path in "${remove_paths[@]}"; do
        if repo_git cat-file -e "$head_commit:$path" 2>/dev/null; then
            restore_paths+=("$path")
        fi
    done
}

reject_linked_worktrees() {
    local worktree_count

    if ! worktree_count="$(repo_git worktree list --porcelain |
        awk '$1 == "worktree" { count++ } END { print count + 0 }')"; then
        error 'failed to inspect linked Git worktrees.'
        return 1
    fi

    if [ "$worktree_count" -gt 1 ]; then
        error 'linked Git worktrees are not supported because local exclude rules are shared.'
        return 1
    fi
}

confirm_head_unchanged() {
    local current_head

    current_head="$(repo_git rev-parse HEAD)" || {
        error 'failed to recheck the current Git commit.'
        return 1
    }
    if [ "$current_head" != "$head_commit" ]; then
        error 'HEAD changed during submission preparation; run the script again.'
        return 1
    fi
}

check_index_flags() {
    if ! repo_git --literal-pathspecs ls-files -v -z -- "${must_be_clean_paths[@]}" |
        (
            local entry
            local flag
            local flag_error=0
            local path

            while IFS= read -r -d '' entry; do
                flag="${entry:0:1}"
                path="${entry:2}"
                # Lowercase ls-files tags mean assume-unchanged; S is skip-worktree.
                case "$flag" in
                    S|[[:lower:]])
                        if [ "$flag_error" -eq 0 ]; then
                            error 'targets that must be clean use skip-worktree or assume-unchanged:'
                        fi
                        printf '  %q\n' "$path" >&2
                        flag_error=1
                        ;;
                esac
            done
            [ "$flag_error" -eq 0 ]
        )
    then
        return 1
    fi
}

check_clean_targets() {
    local dirty_target_status=""
    local status_line

    check_index_flags || return 1

    if ! dirty_target_status="$(repo_git --literal-pathspecs status \
        --porcelain=v1 --untracked-files=all --ignored -- \
        "${must_be_clean_paths[@]}")"; then
        error 'failed to inspect Git status.'
        return 1
    fi

    if [ -n "$dirty_target_status" ]; then
        error 'targets that must be clean contain changes:'
        while IFS= read -r status_line; do
            printf '  %s\n' "$status_line" >&2
        done <<< "$dirty_target_status"
        error 'commit, stash with --all, or remove them before preparing the submission.'
        return 1
    fi
}

check_unmerged_targets() {
    local unmerged_status=""

    if ! unmerged_status="$(repo_git --literal-pathspecs ls-files -u -- \
        "${remove_paths[@]}")"; then
        error 'failed to inspect unmerged Git entries.'
        return 1
    fi

    if [ -n "$unmerged_status" ]; then
        error 'submission-preparation targets contain unmerged Git entries:'
        printf '%s\n' "$unmerged_status" >&2
        return 1
    fi
}

check_removal_target() {
    local directory
    local display_directory
    local parent_directory
    local path="$1"
    local target="$repo_root/$path"

    parent_directory="$(dirname -- "$target")"
    if [ ! -w "$parent_directory" ] || [ ! -x "$parent_directory" ]; then
        error "the parent directory of $path is not writable and searchable."
        return 1
    fi

    if [ -d "$target" ] && [ ! -L "$target" ]; then
        # pipefail reports both find traversal errors and permission failures below.
        if ! find "$target" -type d -print0 |
            (
                local permission_error=0

                while IFS= read -r -d '' directory; do
                    if [ ! -r "$directory" ] || [ ! -w "$directory" ] || [ ! -x "$directory" ]; then
                        printf -v display_directory '%q' "${directory#"$repo_root"/}"
                        error "$display_directory does not have read, write, and search permissions."
                        permission_error=1
                    fi
                done
                [ "$permission_error" -eq 0 ]
            )
        then
            error "permission inspection failed for $path."
            return 1
        fi
    fi
}

preflight_removal() {
    local path

    for path in "${remove_paths[@]}"; do
        check_removal_target "$path" || return 1
    done
}

portable_stat() {
    local bsd_format="$1"
    local gnu_format="$2"
    local output
    local path="$3"

    case "$platform_name" in
        Darwin|FreeBSD|NetBSD|OpenBSD)
            output="$(stat -f "$bsd_format" "$path" 2>/dev/null)" || return 1
            ;;
        Linux)
            output="$(stat -c "$gnu_format" "$path" 2>/dev/null)" || return 1
            ;;
        *)
            if ! output="$(stat -c "$gnu_format" "$path" 2>/dev/null)"; then
                output="$(stat -f "$bsd_format" "$path" 2>/dev/null)" || return 1
            fi
            ;;
    esac

    case "$output" in
        ''|*[!0-9]*) return 1 ;;
        *) printf '%s\n' "$output" ;;
    esac
}

get_file_mode() {
    portable_stat '%Lp' '%a' "$1"
}

get_link_count() {
    portable_stat '%l' '%h' "$1"
}

validate_gitignore() {
    local gitignore_path="$1"

    if [ -L "$gitignore_path" ]; then
        error '.gitignore must not be a symbolic link.'
        return 1
    fi
    if [ ! -e "$gitignore_path" ]; then
        return 0
    fi
    if [ ! -f "$gitignore_path" ] || [ ! -r "$gitignore_path" ]; then
        error '.gitignore must be a readable regular file.'
        return 1
    fi
    if grep -Fqx -- "$managed_begin" "$gitignore_path" ||
        grep -Fqx -- "$managed_end" "$gitignore_path"; then
        error '.gitignore contains a reserved prepare_submission.sh marker.'
        return 1
    fi
}

resolve_exclude_path() {
    local exclude_location

    if ! exclude_location="$(repo_git rev-parse --git-path info/exclude)"; then
        error 'failed to locate the local Git exclude file.'
        return 1
    fi
    case "$exclude_location" in
        /*) printf '%s\n' "$exclude_location" ;;
        *) printf '%s\n' "$repo_root/$exclude_location" ;;
    esac
}

validate_exclude_path() {
    local exclude_directory
    local exclude_path="$1"
    local file_flags
    local link_count

    exclude_directory="$(dirname -- "$exclude_path")"
    if [ ! -d "$exclude_directory" ] || [ ! -w "$exclude_directory" ] || [ ! -x "$exclude_directory" ]; then
        error 'the local Git exclude directory is not writable and searchable.'
        return 1
    fi
    if [ -L "$exclude_path" ] || { [ -e "$exclude_path" ] && [ ! -f "$exclude_path" ]; }; then
        error 'the local Git exclude path is not a regular file.'
        return 1
    fi
    if [ -e "$exclude_path" ] && [ ! -r "$exclude_path" ]; then
        error 'the local Git exclude file is not readable.'
        return 1
    fi

    if [ -f "$exclude_path" ] && [ "$platform_name" = Darwin ]; then
        if ! file_flags="$(stat -f '%Sf' "$exclude_path" 2>/dev/null)"; then
            error 'failed to inspect the local Git exclude file flags.'
            return 1
        fi
        case "$file_flags" in
            *uchg*|*schg*|*uappnd*|*sappnd*)
                error 'the local Git exclude file has an immutable or append-only macOS file flag.'
                return 1
                ;;
        esac
    fi

    if [ -f "$exclude_path" ]; then
        if ! link_count="$(get_link_count "$exclude_path")"; then
            error 'failed to inspect the local Git exclude link count.'
            return 1
        fi
        if [ "$link_count" -gt 1 ]; then
            error 'refusing to replace a hard-linked local Git exclude file.'
            return 1
        fi
    fi
}

copy_preserving_metadata() {
    local destination="$2"
    local source="$1"

    # Preserve mode, ownership, ACLs, and xattrs where cp supports them.
    # Timestamps, inode identity, and ctime are not part of the guarantee.
    case "$platform_name" in
        Linux)
            if ! cp --version 2>/dev/null | grep -Fq 'GNU coreutils'; then
                error 'Linux metadata preservation requires GNU coreutils cp.'
                return 1
            fi
            cp --preserve=all -- "$source" "$destination"
            ;;
        *) cp -p -- "$source" "$destination" ;;
    esac
}

process_managed_blocks() {
    local operation="$1"
    local source="$2"

    awk -v begin="$managed_begin" -v end="$managed_end" \
        -v malformed_status="$managed_block_malformed_status" \
        -v operation="$operation" '
        $0 == begin {
            if (inside) malformed = 1
            inside = 1
            begins++
            next
        }
        $0 == end {
            if (!inside) malformed = 1
            inside = 0
            ends++
            next
        }
        !inside && operation == "rewrite" { print }
        END {
            # The reserved status distinguishes malformed markers from AWK I/O failures.
            if (inside || malformed) exit malformed_status
            if (operation == "require-one" && (begins != 1 || ends != 1)) exit 3
        }
    ' "$source"
}

append_managed_gitignore_block() {
    local destination="$2"
    local gitignore_path="$1"

    {
        printf '%s\n' "$managed_begin"
        cat -- "$gitignore_path"
        printf '\n%s\n' "$managed_end"
    } >> "$destination"
}

prepare_exclude_temp() {
    local exclude_path="$1"
    local exclude_temp="$2"
    local gitignore_path="$3"
    local exclude_mode=""
    local rewrite_status

    if [ -f "$exclude_path" ]; then
        exclude_mode="$(get_file_mode "$exclude_path")" || {
            error 'failed to inspect the local Git exclude file mode.'
            return 1
        }
        copy_preserving_metadata "$exclude_path" "$exclude_temp" || {
            error 'failed to preserve the local Git exclude metadata.'
            return 1
        }
        chmod u+w "$exclude_temp" || {
            error 'failed to make the temporary local Git exclude file writable.'
            return 1
        }
        process_managed_blocks rewrite "$exclude_path" > "$exclude_temp" || {
            rewrite_status=$?
            if [ "$rewrite_status" -eq "$managed_block_malformed_status" ]; then
                error 'the managed block in the local Git exclude file is malformed.'
            else
                error 'failed to write the local Git exclude file.'
            fi
            return 1
        }
    else
        : > "$exclude_temp" || {
            error 'failed to initialize the temporary local Git exclude file.'
            return 1
        }
    fi

    append_managed_gitignore_block "$gitignore_path" "$exclude_temp" || {
        error 'failed to append the managed local Git exclude rules.'
        return 1
    }
    if [ -n "$exclude_mode" ]; then
        chmod "$exclude_mode" "$exclude_temp" || {
            error 'failed to restore the local Git exclude file mode.'
            return 1
        }
    fi
}

preserve_gitignore_rules() (
    local exclude_directory
    local exclude_path="$1"
    local exclude_temp=""
    local gitignore_path="$repo_root/.gitignore"

    cleanup_exclude_temp() {
        if [ -n "$exclude_temp" ]; then
            rm -f -- "$exclude_temp"
        fi
    }
    # Do not inherit the outer ERR handler; this subshell owns temporary cleanup.
    trap - ERR
    trap cleanup_exclude_temp EXIT
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM

    exclude_directory="$(dirname -- "$exclude_path")"

    exclude_temp="$(mktemp "$exclude_directory/prepare_submission.exclude.XXXXXX")" || {
        error 'failed to create a temporary local Git exclude file.'
        return 1
    }

    prepare_exclude_temp "$exclude_path" "$exclude_temp" "$gitignore_path" || return 1
    mv -- "$exclude_temp" "$exclude_path" || {
        error 'failed to install the local Git exclude rules.'
        return 1
    }
    exclude_temp=""

)

print_removal_plan() {
    local path

    printf '%s\n' 'The following paths will be removed:'
    for path in "${remove_paths[@]}"; do
        printf '  %q\n' "$path"
    done
}

report_interrupted_state() {
    if [ "$removal_started" -eq 1 ] && [ "$removal_completed" -ne 1 ]; then
        error 'submission preparation stopped. Some targets may have been removed.'
        if [ "${#restore_paths[@]}" -gt 0 ]; then
            printf '%s\n' 'Restore committed files with:' >&2
            printf '  git --literal-pathspecs -C %q checkout %q --' \
                "$repo_root" "$head_commit" >&2
            printf ' %q' "${restore_paths[@]}" >&2
            printf '\n' >&2
        fi
    fi

    if [ "$gitignore_import_confirmed" -eq 1 ]; then
        printf '%s\n' \
            'The imported .gitignore rules remain active in the local Git exclude file.' >&2
    elif [ -n "$git_exclude_path" ] && [ -f "$git_exclude_path" ] &&
        process_managed_blocks require-one "$git_exclude_path" >/dev/null; then
        printf '%s\n' \
            'The imported .gitignore rules remain active in the local Git exclude file.' >&2
    elif [ -n "$git_exclude_path" ] && [ -f "$git_exclude_path" ] &&
        grep -Fqx -- "$managed_begin" "$git_exclude_path"; then
        printf '%s\n' \
            'A prepare_submission managed marker remains in the local Git exclude file; inspect it before editing ignore rules.' >&2
    fi
}

clear_removal_traps() {
    trap - ERR HUP INT TERM
}

handle_error() {
    local exit_code=$?

    clear_removal_traps
    report_interrupted_state
    exit "$exit_code"
}

handle_signal() {
    local exit_code="$2"
    local signal_name="$1"

    clear_removal_traps
    error "submission preparation was interrupted by $signal_name."
    report_interrupted_state
    exit "$exit_code"
}

install_removal_traps() {
    trap handle_error ERR
    trap 'handle_signal HUP 129' HUP
    trap 'handle_signal INT 130' INT
    trap 'handle_signal TERM 143' TERM
}

remove_targets() {
    local path

    for path in "${remove_paths[@]}"; do
        rm -rf -- "$repo_root/$path" || return 1
    done
}

main() {
    parse_arguments "$@" || return $?
    if [ "$help_requested" -eq 1 ]; then
        print_usage
        return 0
    fi
    platform_name="$(uname -s)" || {
        error 'failed to identify the operating system.'
        return 1
    }
    discover_repository || return 1
    configure_targets
    configure_restore_paths

    reject_linked_worktrees || return 1
    check_clean_targets || return 1
    check_unmerged_targets || return 1
    preflight_removal || return 1
    confirm_head_unchanged || return 1
    validate_gitignore "$repo_root/.gitignore" || return 1
    if [ -e "$repo_root/.gitignore" ]; then
        git_exclude_path="$(resolve_exclude_path)" || return 1
        validate_exclude_path "$git_exclude_path" || return 1
    fi

    # Cover exclude installation too, so a post-install signal reports retained rules.
    install_removal_traps
    if [ -n "$git_exclude_path" ]; then
        if ! preserve_gitignore_rules "$git_exclude_path"; then
            return 1
        fi
        gitignore_import_confirmed=1
        printf '%s\n' 'Preserved .gitignore rules in the local Git exclude file.'
    fi
    print_removal_plan
    # Close the exclude-install/output race windows immediately before deletion.
    check_unmerged_targets
    confirm_head_unchanged
    check_clean_targets
    confirm_head_unchanged
    removal_started=1
    remove_targets
    removal_completed=1
    clear_removal_traps

    printf '%s\n' 'Submission preparation completed.'
}

main "$@"
