#!/usr/bin/env bash

set -Eeuo pipefail

# Manual portability matrix:
#   SUBJECT_BASH="$(command -v bash)" bash .github/tests/prepare_submission_test.sh
#   SUBJECT_BASH=/bin/bash PATH=/bin:/usr/bin /bin/bash .github/tests/prepare_submission_test.sh
# Run the same commands on Linux to exercise GNU stat/cp and optional ACL/xattr tools.

test_dir="$(cd -- "$(dirname -- "$0")" && pwd -P)"
repo_root="$(git -C "$test_dir" rev-parse --show-toplevel)"
subject="$repo_root/prepare_submission.sh"
subject_bash="${SUBJECT_BASH:-$BASH}"
test_root="$(mktemp -d "${TMPDIR:-/tmp}/prepare_submission_tests.XXXXXX")"
managed_begin='# BEGIN prepare_submission.sh managed .gitignore rules'
managed_end='# END prepare_submission.sh managed .gitignore rules'
active_process_id=""
test_label=""
test_skip_reason=""
tests_run=0
unexpected_error_marker="$test_root/.unexpected_error_reported"

cleanup() {
    local exit_status=$?

    if [ -n "$active_process_id" ] && kill -0 "$active_process_id" 2>/dev/null; then
        kill -TERM "$active_process_id" 2>/dev/null || true
        wait "$active_process_id" 2>/dev/null || true
    fi
    if [ "$exit_status" -ne 0 ] && [ "${KEEP_TEST_TMP:-0}" = 1 ]; then
        printf 'Test artifacts preserved at: %s\n' "$test_root" >&2
        return
    fi
    rm -rf -- "$test_root"
}
trap cleanup EXIT

fail() {
    printf 'not ok %d - %s: %s\n' "$tests_run" "$test_label" "$1" >&2
    printf 'Set KEEP_TEST_TMP=1 to preserve test artifacts.\n' >&2
    exit 1
}

report_unexpected_error() {
    local exit_status="$1"
    local line_number="$2"

    trap - ERR
    if [ ! -e "$unexpected_error_marker" ]; then
        : > "$unexpected_error_marker"
        printf 'not ok %d - %s: unexpected command failure at line %s (status %s)\n' \
            "$tests_run" "$test_label" "$line_number" "$exit_status" >&2
        printf 'Set KEEP_TEST_TMP=1 to preserve test artifacts.\n' >&2
    fi
    exit "$exit_status"
}
trap 'report_unexpected_error "$?" "$LINENO"' ERR

run_test() {
    test_label="$1"
    test_skip_reason=""
    tests_run=$((tests_run + 1))
    rm -f -- "$unexpected_error_marker"
    "$2"
    if [ -n "$test_skip_reason" ]; then
        printf 'ok %d - %s # SKIP %s\n' "$tests_run" "$test_label" "$test_skip_reason"
    else
        printf 'ok %d - %s\n' "$tests_run" "$test_label"
    fi
}

skip_test() {
    test_skip_reason="$1"
}

assert_exists() {
    [ -e "$1" ] || [ -L "$1" ] || fail "expected path to exist: $1"
}

assert_absent() {
    if [ -e "$1" ] || [ -L "$1" ]; then
        fail "expected path to be absent: $1"
    fi
}

assert_contains() {
    grep -Fq -- "$2" "$1" || fail "expected $1 to contain: $2"
}

assert_not_contains() {
    if grep -Fq -- "$2" "$1"; then
        fail "expected $1 not to contain: $2"
    fi
}

file_mode() {
    case "$(uname -s)" in
        Darwin|FreeBSD|NetBSD|OpenBSD) stat -f '%Lp' "$1" ;;
        *) stat -c '%a' "$1" ;;
    esac
}

exclude_hash() {
    git hash-object "$1/.git/info/exclude"
}

create_fixture() {
    local fixture="$test_root/$1"

    mkdir -p "$fixture/.github/workflows"
    git -C "$fixture" init -q
    cp "$subject" "$fixture/prepare_submission.sh"
    chmod +x "$fixture/prepare_submission.sh"
    printf '%s\n' '# Test fixture' > "$fixture/README.md"
    printf '%s\n' '[tool.test]' > "$fixture/pyproject.toml"
    printf '%s\n' '.env' '.venv/' '*.tmp' > "$fixture/.gitignore"
    printf '%s\n' 'name: test' > "$fixture/.github/workflows/test.yml"
    printf '%s\n' '{"extends": ["config:recommended"]}' > "$fixture/renovate.json"
    printf '%s\n' 'print("solution")' > "$fixture/solution.py"
    commit_fixture "$fixture" 'test fixture' .
}

commit_fixture() {
    local fixture="$1"
    local message="$2"
    shift 2

    git -C "$fixture" add -- "$@"
    git -C "$fixture" -c user.name=Test -c user.email=test@example.invalid \
        commit -qm "$message"
}

restore_fixture_head() {
    git -C "$1" checkout -q HEAD -- .
}

run_subject() {
    local fixture="$1"
    local output_prefix="$2"
    shift 2

    (
        cd "$fixture"
        "$subject_bash" ./prepare_submission.sh "$@" \
            > "$output_prefix.stdout" 2> "$output_prefix.stderr"
    )
}

assert_targets_intact() {
    local fixture="$1"

    assert_exists "$fixture/.github"
    assert_exists "$fixture/README.md"
    assert_exists "$fixture/renovate.json"
    assert_exists "$fixture/pyproject.toml"
    assert_exists "$fixture/.gitignore"
    assert_exists "$fixture/prepare_submission.sh"
}

assert_preflight_rejection_preserved_state() {
    local before_hash="$2"
    local fixture="$1"

    assert_targets_intact "$fixture"
    [ "$before_hash" = "$(exclude_hash "$fixture")" ] ||
        fail 'preflight rejection changed the local Git exclude file'
}

assert_managed_rules_active() {
    local begin_count
    local end_count
    local fixture="$1"

    begin_count="$(grep -Fxc -- "$managed_begin" "$fixture/.git/info/exclude")" ||
        fail 'failed to count managed block begin markers'
    end_count="$(grep -Fxc -- "$managed_end" "$fixture/.git/info/exclude")" ||
        fail 'failed to count managed block end markers'
    [ "$begin_count" -eq 1 ] || fail 'managed block must have exactly one begin marker'
    [ "$end_count" -eq 1 ] || fail 'managed block must have exactly one end marker'
    git -C "$fixture" check-ignore -q -- .env || fail '.env ignore rule must be active'
}

wait_for_output() {
    local file="$1"
    local pattern="$2"
    local attempt=0

    while [ "$attempt" -lt 50 ]; do
        if grep -Fq -- "$pattern" "$file" 2>/dev/null; then
            return 0
        fi
        if ! kill -0 "$active_process_id" 2>/dev/null; then
            fail "subject exited before readiness marker: $pattern"
        fi
        sleep 0.1
        attempt=$((attempt + 1))
    done
    fail "timed out waiting for readiness marker: $pattern"
}

assert_help_option() {
    local fixture="$test_root/$1"
    local option="$2"

    create_fixture "$1"
    run_subject "$fixture" run "$option"
    assert_contains "$fixture/run.stdout" 'Usage: prepare_submission.sh [-K | --keep-readme]'
    assert_contains "$fixture/run.stdout" '-K, --keep-readme'
    assert_contains "$fixture/run.stdout" '-h, --help'
    [ ! -s "$fixture/run.stderr" ] || fail "$option wrote unexpected stderr output"
    assert_targets_intact "$fixture"
}

test_help_options() {
    assert_help_option help_short -h
    assert_help_option help_long --help
}

test_rejects_invalid_options() {
    local fixture="$test_root/unknown_option"
    local before_hash
    create_fixture unknown_option
    before_hash="$(exclude_hash "$fixture")"

    if run_subject "$fixture" run --unknown; then
        fail 'an unknown option must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'unknown option: --unknown'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"

    fixture="$test_root/multiple_options"
    create_fixture multiple_options
    before_hash="$(exclude_hash "$fixture")"
    if run_subject "$fixture" run -K --keep-readme; then
        fail 'multiple options must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'only one option may be specified'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

test_normal_cleanup() {
    local fixture="$test_root/normal"
    create_fixture normal

    printf '%s\n' 'local-only.txt' >> "$fixture/.git/info/exclude"
    printf '%s\n' secret > "$fixture/.env"
    printf '%s\n' dirty >> "$fixture/.github/workflows/test.yml"
    printf '%s\n' untracked > "$fixture/.github/local.txt"
    printf '%s\n' ignored > "$fixture/.github/ignored.tmp"
    run_subject "$fixture" run

    assert_absent "$fixture/.github"
    assert_absent "$fixture/README.md"
    assert_absent "$fixture/renovate.json"
    assert_absent "$fixture/pyproject.toml"
    assert_absent "$fixture/.gitignore"
    assert_absent "$fixture/prepare_submission.sh"
    assert_exists "$fixture/.env"
    assert_exists "$fixture/solution.py"
    [ "$(cat "$fixture/.env")" = secret ] || fail '.env content changed'
    [ "$(cat "$fixture/solution.py")" = 'print("solution")' ] ||
        fail 'solution.py content changed'
    assert_managed_rules_active "$fixture"
    assert_contains "$fixture/.git/info/exclude" 'local-only.txt'
}

test_quoted_fixture_path() {
    local fixture="$test_root/quoted path 日本語"
    create_fixture 'quoted path 日本語'

    run_subject "$fixture" run
    assert_absent "$fixture/.github"
    assert_absent "$fixture/pyproject.toml"
    assert_absent "$fixture/.gitignore"
    assert_absent "$fixture/prepare_submission.sh"
    assert_exists "$fixture/solution.py"
}

test_clean_target_rejection() {
    local fixture="$test_root/dirty"
    local before_hash
    create_fixture dirty
    before_hash="$(exclude_hash "$fixture")"

    printf '%s\n' '# dirty' >> "$fixture/pyproject.toml"
    if run_subject "$fixture" run; then
        fail 'dirty target must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'pyproject.toml'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

test_dirty_renovate_rejection() {
    local fixture="$test_root/dirty_renovate"
    local before_hash
    create_fixture dirty_renovate
    before_hash="$(exclude_hash "$fixture")"

    printf '%s\n' '{"dirty": true}' > "$fixture/renovate.json"
    if run_subject "$fixture" run; then
        fail 'dirty renovate.json must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'renovate.json'
    assert_contains "$fixture/renovate.json" '"dirty": true'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

test_dirty_readme_rejection() {
    local fixture="$test_root/dirty_readme"
    local before_hash
    create_fixture dirty_readme
    before_hash="$(exclude_hash "$fixture")"

    printf '%s\n' '# Unsaved documentation' > "$fixture/README.md"
    if run_subject "$fixture" run; then
        fail 'dirty README.md must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'README.md'
    assert_contains "$fixture/README.md" 'Unsaved documentation'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

assert_keep_readme_option() {
    local fixture="$test_root/$1"
    local option="$2"

    create_fixture "$1"
    printf '%s\n' '# Project documentation' > "$fixture/README.md"
    run_subject "$fixture" run "$option"

    assert_exists "$fixture/README.md"
    assert_contains "$fixture/README.md" 'Project documentation'
    assert_absent "$fixture/.github"
    assert_absent "$fixture/renovate.json"
    assert_absent "$fixture/pyproject.toml"
    assert_absent "$fixture/.gitignore"
    assert_absent "$fixture/prepare_submission.sh"
    assert_exists "$fixture/solution.py"
    assert_not_contains "$fixture/run.stdout" 'README.md'
    assert_managed_rules_active "$fixture"
}

test_keep_readme_options() {
    assert_keep_readme_option keep_readme_short -K
    assert_keep_readme_option keep_readme_long --keep-readme
}

test_managed_block_replacement() {
    local before_hash
    local fixture="$test_root/managed"
    local marker_count
    create_fixture managed

    printf '%s\n' 'old.review' >> "$fixture/.gitignore"
    commit_fixture "$fixture" 'add old ignore rule' .gitignore
    printf '%s\n' old > "$fixture/old.review"
    run_subject "$fixture" first

    restore_fixture_head "$fixture"
    awk '$0 != "old.review"' "$fixture/.gitignore" > "$fixture/.gitignore.next"
    mv "$fixture/.gitignore.next" "$fixture/.gitignore"
    printf '%s\n' 'new.review' >> "$fixture/.gitignore"
    commit_fixture "$fixture" 'replace ignore rule' .gitignore
    printf '%s\n' new > "$fixture/new.review"
    run_subject "$fixture" second

    if git -C "$fixture" check-ignore -q old.review; then
        fail 'old managed ignore rule must be removed'
    fi
    git -C "$fixture" check-ignore -q new.review || fail 'new ignore rule must be active'
    marker_count="$(grep -Fxc -- "$managed_begin" "$fixture/.git/info/exclude")" ||
        fail 'failed to count managed blocks'
    [ "$marker_count" -eq 1 ] || fail 'managed block must occur exactly once'

    restore_fixture_head "$fixture"
    before_hash="$(exclude_hash "$fixture")"
    run_subject "$fixture" third
    [ "$before_hash" = "$(exclude_hash "$fixture")" ] ||
        fail 'identical rerun changed local exclude content'
}

test_marker_validation() {
    local fixture="$test_root/marker"
    local before_hash
    create_fixture marker

    printf '%s\n' "$managed_begin" >> "$fixture/.gitignore"
    commit_fixture "$fixture" 'add reserved marker' .gitignore
    before_hash="$(exclude_hash "$fixture")"
    if run_subject "$fixture" run; then
        fail 'reserved marker must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'reserved prepare_submission.sh marker'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

test_malformed_block_rejection() {
    local fixture="$test_root/malformed"
    create_fixture malformed

    printf '%s\n' "$managed_begin" >> "$fixture/.git/info/exclude"
    if run_subject "$fixture" run; then
        fail 'malformed managed block must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'managed block in the local Git exclude file is malformed'
    assert_not_contains "$fixture/run.stderr" 'imported .gitignore rules remain active'
    assert_targets_intact "$fixture"
}

test_linked_worktree_rejection() {
    local fixture="$test_root/worktree"
    local before_hash
    create_fixture worktree
    before_hash="$(exclude_hash "$fixture")"

    git -C "$fixture" worktree add -q -b linked-test "$test_root/linked"
    if run_subject "$fixture" run; then
        fail 'main worktree must reject linked worktree configuration'
    fi
    assert_contains "$fixture/run.stderr" 'linked Git worktrees are not supported'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

test_mode_preservation() {
    local fixture="$test_root/mode"
    create_fixture mode

    chmod 640 "$fixture/.git/info/exclude"
    run_subject "$fixture" run
    [ "$(file_mode "$fixture/.git/info/exclude")" = 640 ] ||
        fail 'local exclude mode must be preserved'
}

test_xattr_preservation() {
    local fixture="$test_root/xattr"
    create_fixture xattr

    case "$(uname -s)" in
        Darwin)
            if ! command -v xattr >/dev/null 2>&1; then
                skip_test 'macOS xattr utility is unavailable'
                return 0
            fi
            if ! xattr -w com.example.prepare-submission preserved \
                "$fixture/.git/info/exclude" 2>/dev/null; then
                skip_test 'xattrs are unavailable on this macOS filesystem'
                return 0
            fi
            run_subject "$fixture" run
            [ "$(xattr -p com.example.prepare-submission "$fixture/.git/info/exclude")" = preserved ] ||
                fail 'macOS xattr must be preserved'
            ;;
        Linux)
            if ! command -v setfattr >/dev/null 2>&1 || ! command -v getfattr >/dev/null 2>&1; then
                skip_test 'Linux xattr utilities are unavailable'
                return 0
            fi
            if ! setfattr -n user.prepare_submission -v preserved \
                "$fixture/.git/info/exclude" 2>/dev/null; then
                skip_test 'xattrs are unavailable on this Linux filesystem'
                return 0
            fi
            run_subject "$fixture" run
            getfattr --only-values -n user.prepare_submission "$fixture/.git/info/exclude" |
                grep -Fqx preserved || fail 'Linux xattr must be preserved'
            ;;
        *) skip_test 'xattr preservation is not defined for this operating system' ;;
    esac
}

test_acl_preservation() {
    local acl_before
    local acl_after
    local exclude_path
    local fixture="$test_root/acl"
    create_fixture acl
    exclude_path="$fixture/.git/info/exclude"

    case "$(uname -s)" in
        Darwin)
            if ! chmod +a "$(id -un) allow read,write" "$exclude_path" 2>/dev/null; then
                skip_test 'ACLs are unavailable on this macOS filesystem'
                return 0
            fi
            acl_before="$(ls -lde "$exclude_path" | sed -n '2,$p')"
            run_subject "$fixture" run
            acl_after="$(ls -lde "$exclude_path" | sed -n '2,$p')"
            ;;
        Linux)
            if ! command -v setfacl >/dev/null 2>&1 || ! command -v getfacl >/dev/null 2>&1; then
                skip_test 'Linux ACL utilities are unavailable'
                return 0
            fi
            if ! setfacl -m "u:$(id -un):rw" "$exclude_path" 2>/dev/null; then
                skip_test 'ACLs are unavailable on this Linux filesystem'
                return 0
            fi
            acl_before="$(getfacl -cp "$exclude_path")"
            run_subject "$fixture" run
            acl_after="$(getfacl -cp "$exclude_path")"
            ;;
        *)
            skip_test 'ACL preservation is not defined for this operating system'
            return 0
            ;;
    esac
    [ -n "$acl_before" ] || fail 'ACL fixture must contain an access control entry'
    [ "$acl_before" = "$acl_after" ] || fail 'local exclude ACL must be preserved'
}

test_permission_rejection() {
    local fixture="$test_root/permissions"
    local before_hash
    create_fixture permissions

    if [ "$(id -u)" -eq 0 ]; then
        skip_test 'permission checks require a non-root user'
        return 0
    fi
    before_hash="$(exclude_hash "$fixture")"
    chmod a-w "$fixture/.github/workflows"
    if run_subject "$fixture" run; then
        chmod u+w "$fixture/.github/workflows"
        fail 'unwritable nested directory must be rejected'
    fi
    chmod u+w "$fixture/.github/workflows"
    assert_contains "$fixture/run.stderr" '.github/workflows'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

test_index_flag_rejection() {
    local fixture="$test_root/index_flag"
    local before_hash
    create_fixture index_flag
    before_hash="$(exclude_hash "$fixture")"

    git -C "$fixture" update-index --assume-unchanged pyproject.toml
    printf '%s\n' '# hidden change' >> "$fixture/pyproject.toml"
    if run_subject "$fixture" run; then
        fail 'assume-unchanged target must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'assume-unchanged'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

test_skip_worktree_rejection() {
    local fixture="$test_root/skip_worktree"
    local before_hash
    create_fixture skip_worktree
    before_hash="$(exclude_hash "$fixture")"

    git -C "$fixture" update-index --skip-worktree pyproject.toml
    if run_subject "$fixture" run; then
        fail 'skip-worktree target must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'skip-worktree'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

test_unmerged_rejection() {
    local base_blob
    local fixture="$test_root/unmerged"
    local ours_blob
    local theirs_blob
    local before_hash
    create_fixture unmerged
    before_hash="$(exclude_hash "$fixture")"

    base_blob="$(printf base | git -C "$fixture" hash-object -w --stdin)"
    ours_blob="$(printf ours | git -C "$fixture" hash-object -w --stdin)"
    theirs_blob="$(printf theirs | git -C "$fixture" hash-object -w --stdin)"
    printf '100644 %s 1\t.github/conflict.yml\n100644 %s 2\t.github/conflict.yml\n100644 %s 3\t.github/conflict.yml\n' \
        "$base_blob" "$ours_blob" "$theirs_blob" |
        git -C "$fixture" update-index --index-info
    if run_subject "$fixture" run; then
        fail 'unmerged target must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'unmerged Git entries'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

test_hardlinked_exclude_rejection() {
    local fixture="$test_root/hardlink"
    create_fixture hardlink

    ln "$fixture/.git/info/exclude" "$fixture/.git/info/exclude.link"
    if run_subject "$fixture" run; then
        fail 'hard-linked exclude must be rejected'
    fi
    assert_contains "$fixture/run.stderr" 'hard-linked local Git exclude file'
    assert_targets_intact "$fixture"
}

test_failed_removal_report() {
    local fixture="$test_root/removal_failure"
    create_fixture removal_failure

    if CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        rm() { return 7; }
        export -f rm
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr"; then
        fail 'simulated removal failure must fail'
    fi
    assert_contains "$fixture/stderr" 'Some targets may have been removed'
    assert_contains "$fixture/stderr" 'imported .gitignore rules remain active'
    assert_targets_intact "$fixture"
}

test_failed_exclude_install_cleanup() {
    local before_hash
    local fixture="$test_root/exclude_install_failure"
    create_fixture exclude_install_failure
    before_hash="$(exclude_hash "$fixture")"

    if CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        mv() { return 7; }
        export -f mv
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr"; then
        fail 'simulated exclude installation failure must fail'
    fi
    assert_contains "$fixture/stderr" 'failed to install the local Git exclude rules'
    [ "$before_hash" = "$(exclude_hash "$fixture")" ] ||
        fail 'failed exclude installation changed the original exclude file'
    if find "$fixture/.git/info" -name 'prepare_submission.exclude.*' -print -quit |
        grep -q .; then
        fail 'failed exclude installation left a temporary file'
    fi
    assert_targets_intact "$fixture"
}

test_output_failure_after_import() {
    local fixture="$test_root/output_failure"
    create_fixture output_failure

    if CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh >&-
    ' 2> "$fixture/stderr"; then
        fail 'closed stdout must make the subject fail'
    fi
    assert_contains "$fixture/stderr" 'imported .gitignore rules remain active'
    assert_managed_rules_active "$fixture"
    assert_targets_intact "$fixture"
}

test_concurrent_protected_change_rejection() {
    local exit_status
    local fixture="$test_root/concurrent_change"
    create_fixture concurrent_change

    CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        mv() {
            command mv "$@"
            printf "%s\n" ready > "$CASE_DIR/mv.ready"
            sleep 2
        }
        export -f mv
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr" &
    active_process_id=$!
    wait_for_output "$fixture/mv.ready" ready
    printf '%s\n' '# concurrent unsaved work' >> "$fixture/pyproject.toml"
    if wait "$active_process_id"; then
        exit_status=0
    else
        exit_status=$?
    fi
    active_process_id=""

    [ "$exit_status" -ne 0 ] || fail 'concurrent protected change must stop removal'
    assert_contains "$fixture/pyproject.toml" '# concurrent unsaved work'
    assert_contains "$fixture/stderr" 'pyproject.toml'
    assert_contains "$fixture/stderr" 'imported .gitignore rules remain active'
    assert_managed_rules_active "$fixture"
    assert_targets_intact "$fixture"
}

test_change_during_plan_output_rejection() {
    local exit_status
    local fixture="$test_root/plan_output_change"
    create_fixture plan_output_change

    CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        printf() {
            command printf "$@"
            if [ "$#" -ge 2 ] && [ "$1" = "%s\n" ] &&
                [ "$2" = "The following paths will be removed:" ]; then
                command printf "%s\n" ready > "$CASE_DIR/plan.ready"
                sleep 2
            fi
        }
        export -f printf
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr" &
    active_process_id=$!
    wait_for_output "$fixture/plan.ready" ready
    printf '%s\n' '# edit while plan output is blocked' >> "$fixture/pyproject.toml"
    if wait "$active_process_id"; then
        exit_status=0
    else
        exit_status=$?
    fi
    active_process_id=""

    [ "$exit_status" -ne 0 ] || fail 'change during plan output must stop removal'
    assert_contains "$fixture/pyproject.toml" '# edit while plan output is blocked'
    assert_contains "$fixture/stderr" 'pyproject.toml'
    assert_managed_rules_active "$fixture"
    assert_targets_intact "$fixture"
}

test_commit_during_final_status_rejection() {
    local exit_status
    local fixture="$test_root/final_status_commit"
    create_fixture final_status_commit

    CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        git() {
            case " $* " in
                *" status "*)
                    if [ ! -e "$CASE_DIR/status.seen" ]; then
                        : > "$CASE_DIR/status.seen"
                        command git "$@"
                    else
                        command git "$@" || return $?
                        command printf "%s\n" ready > "$CASE_DIR/status.ready"
                        sleep 2
                    fi
                    ;;
                *) command git "$@" ;;
            esac
        }
        export -f git
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr" &
    active_process_id=$!
    wait_for_output "$fixture/status.ready" ready
    printf '%s\n' '# committed during final status' >> "$fixture/pyproject.toml"
    commit_fixture "$fixture" 'concurrent protected commit' pyproject.toml
    if wait "$active_process_id"; then
        exit_status=0
    else
        exit_status=$?
    fi
    active_process_id=""

    [ "$exit_status" -ne 0 ] || fail 'concurrent HEAD change must stop removal'
    assert_contains "$fixture/stderr" 'HEAD changed during submission preparation'
    assert_contains "$fixture/pyproject.toml" '# committed during final status'
    assert_managed_rules_active "$fixture"
    assert_targets_intact "$fixture"
}

test_recovery_command_restores_removed_target() {
    local actual_command
    local canonical_fixture
    local expected_command
    local fixture="$test_root/recovery_execution"
    local original_head
    create_fixture recovery_execution
    original_head="$(git -C "$fixture" rev-parse HEAD)"

    if CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        rm() {
            case "$*" in
                *"/.github") command rm "$@" ;;
                *) return 7 ;;
            esac
        }
        export -f rm
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr"; then
        fail 'simulated second-target removal failure must fail'
    fi
    assert_absent "$fixture/.github"
    assert_contains "$fixture/stderr" 'Restore committed files with:'
    canonical_fixture="$(git -C "$fixture" rev-parse --show-toplevel)"
    actual_command="$(awk '
        $0 == "Restore committed files with:" { getline; print; exit }
    ' "$fixture/stderr")"
    expected_command="$(
        printf '  git --literal-pathspecs -C %q checkout %q --' \
            "$canonical_fixture" "$original_head"
        printf ' %q' .github README.md pyproject.toml .gitignore renovate.json prepare_submission.sh
    )"
    [ "$actual_command" = "$expected_command" ] ||
        fail 'reported recovery command does not match the removable HEAD paths'
    git --literal-pathspecs -C "$fixture" checkout "$original_head" -- \
        .github README.md pyproject.toml .gitignore renovate.json prepare_submission.sh
    assert_targets_intact "$fixture"
}

test_keep_readme_recovery_omits_readme() {
    local actual_command
    local fixture="$test_root/keep_readme_recovery"
    create_fixture keep_readme_recovery
    printf '%s\n' '# Project documentation' > "$fixture/README.md"

    if CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        rm() {
            case "$*" in
                *"/.github") command rm "$@" ;;
                *) return 7 ;;
            esac
        }
        export -f rm
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh -K
    ' > "$fixture/stdout" 2> "$fixture/stderr"; then
        fail 'simulated removal failure must fail'
    fi
    assert_absent "$fixture/.github"
    assert_exists "$fixture/README.md"
    assert_contains "$fixture/README.md" 'Project documentation'
    actual_command="$(awk '
        $0 == "Restore committed files with:" { getline; print; exit }
    ' "$fixture/stderr")"
    [ -n "$actual_command" ] || fail 'recovery command was not reported'
    case "$actual_command" in
        *README.md*) fail 'README.md must be omitted from the recovery command' ;;
    esac
    case "$actual_command" in
        *pyproject.toml*) ;;
        *) fail 'recovery command must include pyproject.toml' ;;
    esac
}

test_recovery_omits_untracked_head_paths() {
    local fixture="$test_root/recovery_paths"
    create_fixture recovery_paths

    git -C "$fixture" rm -qr .github pyproject.toml .gitignore
    commit_fixture "$fixture" 'remove optional preparation targets' .
    if CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        rm() { return 7; }
        export -f rm
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr"; then
        fail 'simulated removal failure must fail'
    fi
    assert_contains "$fixture/stderr" 'prepare_submission.sh'
    assert_contains "$fixture/stderr" 'README.md'
    assert_contains "$fixture/stderr" 'renovate.json'
    assert_not_contains "$fixture/stderr" 'pyproject.toml'
    assert_not_contains "$fixture/stderr" '.gitignore'
    assert_not_contains "$fixture/stderr" '.github'
}

assert_signal_during_removal() {
    local exit_status
    local expected_status="$2"
    local signal_name="$1"
    local fixture="$test_root/signal_$signal_name"
    create_fixture "signal_$signal_name"

    CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        rm() {
            command printf "%s\n" ready > "$CASE_DIR/removal.ready"
            sleep 2
            command rm "$@"
        }
        export -f rm
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr" &
    active_process_id=$!
    wait_for_output "$fixture/removal.ready" ready
    kill -s "$signal_name" "$active_process_id"
    if wait "$active_process_id"; then
        exit_status=0
    else
        exit_status=$?
    fi
    active_process_id=""

    [ "$exit_status" -eq "$expected_status" ] ||
        fail "$signal_name must return status $expected_status"
    assert_contains "$fixture/stderr" "interrupted by $signal_name"
    assert_contains "$fixture/stderr" 'Restore committed files with:'
}

test_term_handler() {
    assert_signal_during_removal TERM 143
}

test_hup_handler() {
    assert_signal_during_removal HUP 129
}

test_int_handler() {
    local exit_status
    local fixture="$test_root/signal_INT"
    create_fixture signal_INT

    if CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        rm() {
            command printf "%s\n" ready > "$CASE_DIR/removal.ready"
            sleep 2
            command rm "$@"
        }
        export -f rm
        parent_pid=$$
        (
            attempt=0
            while [ "$attempt" -lt 100 ]; do
                if grep -Fq ready "$CASE_DIR/removal.ready" 2>/dev/null; then
                    kill -INT "$parent_pid"
                    exit
                fi
                sleep 0.05
                attempt=$((attempt + 1))
            done
        ) &
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr"; then
        exit_status=0
    else
        exit_status=$?
    fi

    [ "$exit_status" -eq 130 ] || fail 'INT must return status 130'
    assert_contains "$fixture/stderr" 'interrupted by INT'
    assert_contains "$fixture/stderr" 'Restore committed files with:'
}

test_signal_during_exclude_install() {
    local exit_status
    local fixture="$test_root/exclude_signal"
    create_fixture exclude_signal

    CASE_DIR="$fixture" SUBJECT_BASH="$subject_bash" bash -c '
        mv() {
            command mv "$@"
            sleep 2
        }
        export -f mv
        cd "$CASE_DIR"
        exec "$SUBJECT_BASH" ./prepare_submission.sh
    ' > "$fixture/stdout" 2> "$fixture/stderr" &
    active_process_id=$!
    wait_for_output "$fixture/.git/info/exclude" "$managed_begin"
    kill -TERM "$active_process_id"
    if wait "$active_process_id"; then
        exit_status=0
    else
        exit_status=$?
    fi
    active_process_id=""

    [ "$exit_status" -eq 143 ] || fail 'TERM during exclude install must return status 143'
    assert_contains "$fixture/stderr" 'interrupted by TERM'
    assert_contains "$fixture/stderr" 'imported .gitignore rules remain active'
    assert_managed_rules_active "$fixture"
    assert_targets_intact "$fixture"
}

test_protected_exclude_rejection() {
    local fixture="$test_root/immutable"
    create_fixture immutable

    if [ "$(uname -s)" != Darwin ]; then
        skip_test 'macOS file flags are unavailable'
        return 0
    fi
    for flag in uchg uappnd; do
        if ! chflags "$flag" "$fixture/.git/info/exclude" 2>/dev/null; then
            skip_test "$flag is unavailable on this macOS filesystem"
            return 0
        fi
        if run_subject "$fixture" "$flag"; then
            chflags "no$flag" "$fixture/.git/info/exclude"
            fail "$flag exclude must be rejected"
        fi
        chflags "no$flag" "$fixture/.git/info/exclude"
        assert_contains "$fixture/$flag.stderr" 'immutable or append-only macOS file flag'
        if find "$fixture/.git/info" -name 'prepare_submission.exclude.*' -print -quit |
            grep -q .; then
            fail "$flag exclude rejection left a temporary file"
        fi
        assert_targets_intact "$fixture"
    done
}

test_dangling_gitignore_symlink() {
    local fixture="$test_root/dangling"
    local before_hash
    create_fixture dangling

    rm "$fixture/.gitignore"
    ln -s missing-ignore-file "$fixture/.gitignore"
    commit_fixture "$fixture" 'replace gitignore with dangling symlink' .gitignore
    before_hash="$(exclude_hash "$fixture")"
    if run_subject "$fixture" run; then
        fail 'dangling .gitignore symlink must be rejected'
    fi
    assert_contains "$fixture/run.stderr" '.gitignore must not be a symbolic link'
    assert_preflight_rejection_preserved_state "$fixture" "$before_hash"
}

run_test 'shows help for short and long options' test_help_options
run_test 'rejects unknown and multiple options' test_rejects_invalid_options
run_test 'removes targets and preserves non-target files' test_normal_cleanup
run_test 'handles spaces and non-ASCII fixture paths' test_quoted_fixture_path
run_test 'rejects modified targets that must be clean' test_clean_target_rejection
run_test 'rejects a modified renovate.json' test_dirty_renovate_rejection
run_test 'rejects a modified README.md' test_dirty_readme_rejection
run_test 'keeps a modified README with short and long options' test_keep_readme_options
run_test 'replaces managed rules byte-for-byte idempotently' test_managed_block_replacement
run_test 'rejects reserved markers in .gitignore' test_marker_validation
run_test 'rejects malformed managed exclude blocks' test_malformed_block_rejection
run_test 'rejects repositories with linked worktrees' test_linked_worktree_rejection
run_test 'preserves local exclude mode' test_mode_preservation
run_test 'preserves local exclude xattrs' test_xattr_preservation
run_test 'preserves local exclude ACLs' test_acl_preservation
run_test 'rejects insufficient nested permissions' test_permission_rejection
run_test 'rejects assume-unchanged targets' test_index_flag_rejection
run_test 'rejects skip-worktree targets' test_skip_worktree_rejection
run_test 'rejects unmerged target entries' test_unmerged_rejection
run_test 'rejects hard-linked local exclude files' test_hardlinked_exclude_rejection
run_test 'reports partial removal and retained exclude rules' test_failed_removal_report
run_test 'cleans up after exclude installation failure' test_failed_exclude_install_cleanup
run_test 'reports retained rules after an output failure' test_output_failure_after_import
run_test 'rejects protected changes made during exclude installation' test_concurrent_protected_change_rejection
run_test 'rejects protected changes made during plan output' test_change_during_plan_output_rejection
run_test 'rejects a commit made during the final status check' test_commit_during_final_status_rejection
run_test 'recovery command restores a removed target' test_recovery_command_restores_removed_target
run_test 'omits a kept README from recovery output' test_keep_readme_recovery_omits_readme
run_test 'omits absent HEAD paths from recovery command' test_recovery_omits_untracked_head_paths
run_test 'handles TERM during removal' test_term_handler
run_test 'handles HUP during removal' test_hup_handler
run_test 'handles INT during removal' test_int_handler
run_test 'handles TERM during exclude installation' test_signal_during_exclude_install
run_test 'rejects protected macOS exclude files' test_protected_exclude_rejection
run_test 'rejects dangling .gitignore symlinks' test_dangling_gitignore_symlink

printf '1..%d\n' "$tests_run"
