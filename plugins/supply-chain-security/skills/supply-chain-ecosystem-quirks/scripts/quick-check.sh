#!/usr/bin/env bash
# Ecosystem quick-check for the supply-chain-ecosystem-quirks skill.
#
# Usage: bash scripts/quick-check.sh [--pth-only] [--env <prefix>]... [project-dir]
#
#   project-dir   project root to inspect (default: current directory)
#   --pth-only    run only the Python .pth/.start startup-code scan
#   --env PREFIX  also scan this Python environment (venv, conda or pixi env);
#                 repeatable
#
# Prints one line per result: "<ecosystem> FAIL|WARN|INFO: <message>".
# Exit status: 0 = no FAIL, 1 = at least one FAIL, 2 = usage error.
# Read-only: it never installs, builds, or runs project code, and it inspects
# Python with -I -S so the scan itself does not execute .pth files.

pth_only=no
project=.
extra_envs=()
while [ $# -gt 0 ]; do
  case $1 in
    --pth-only) pth_only=yes ;;
    --env)
      [ $# -ge 2 ] || { echo "usage: --env needs a prefix" >&2; exit 2; }
      # Resolve now: relative prefixes are relative to the caller, not project-dir.
      extra_envs+=("$(cd "$2" 2>/dev/null && pwd || printf '%s' "$2")"); shift ;;
    -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) project=$1 ;;
  esac
  shift
done
cd "$project" || { echo "cannot cd to $project" >&2; exit 2; }

fails=0
say() { # ecosystem level message
  printf '%s %s: %s\n' "$1" "$2" "$3"
  if [ "$2" = FAIL ]; then fails=$((fails + 1)); fi
}

# CI configuration files, and the wider set that also holds build scripts.
ci_files=()
for f in .github/workflows/*.yml .github/workflows/*.yaml .gitlab-ci.yml; do
  [ -f "$f" ] && ci_files+=("$f")
done
build_files=("${ci_files[@]}")
for f in Makefile *.sh; do
  [ -f "$f" ] && build_files+=("$f")
done

# Print each logical command as "file:line:command", line being where it starts.
# Joins shell "\" continuations, YAML folded (>) block scalars and multi-line
# plain scalars; keeps each line of a literal (|) block separate; drops comments.
logical() {
  [ $# -gt 0 ] || return 0
  awk '
    function lead(s) { match(s, /^[ \t]*/); return RLENGTH }
    function strip(s) {
      if (s ~ /^[ \t]*#/) return ""
      sub(/[ \t]+#.*$/, "", s); sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s)
      return s
    }
    function out() { if (buf != "") print fname ":" start ":" buf; buf = "" }
    function add(s, n,   c) { # append a piece; returns 1 when it ends with a backslash
      c = (s ~ /\\$/)
      if (c) { sub(/\\$/, "", s); sub(/[ \t]+$/, "", s) }
      if (s != "") { if (buf == "") { buf = s; start = n; fname = FILENAME } else buf = buf " " s }
      return c
    }
    FNR == 1 { out(); mode = ""; cont = 0; yaml = (FILENAME ~ /[.]ya?ml$/) }
    {
      line = $0; sub(/\r$/, "", line); ind = lead(line); blank = (line ~ /^[ \t]*$/)
      if (cont) { cont = add(strip(line), FNR); if (!cont && mode != "fold" && mode != "plain") out(); next }
      if (mode != "") {
        if (blank) { if (mode != "lit") out(); next }
        if (ind > keyind) {
          if (mode == "lit") { cont = add(strip(line), FNR); if (!cont) out() }
          else add(strip(line), FNR)
          next
        }
        out(); mode = ""
      }
      if (blank) next
      if (yaml && line ~ /^[ \t]*-[ \t]+[|>][-+0-9]*[ \t]*(#.*)?$/) {
        keyind = ind; mode = (line ~ /^[ \t]*-[ \t]+[|]/) ? "lit" : "fold"; next
      }
      if (yaml && match(line, /^[ \t]*(-[ \t]+)?[^ \t#"\047][^:#]*:([ \t]|$)/)) {
        rest = substr(line, RLENGTH + 1); keyind = ind
        if (line ~ /^[ \t]*-[ \t]/) keyind = ind + 1 + lead(substr(line, ind + 2))
        if (rest ~ /^[ \t]*[|>][-+0-9]*[ \t]*(#.*)?$/) { mode = (rest ~ /^[ \t]*[|]/) ? "lit" : "fold"; next }
        cont = add(strip(line), FNR)
        if (!cont) { if (rest ~ /^[ \t]*(#.*)?$/) out(); else mode = "plain" }
        next
      }
      cont = add(strip(line), FNR)
      if (!cont) out()
    }
    END { out() }' "$@" 2>/dev/null
}
# Split each logical command into single commands at &&, ||, ;, |, ( and ) outside
# shell quotes and ${{ }} expressions; each keeps its logical command's start line.
# A YAML-quoted scalar is unquoted first. YAML step names are left whole.
commands() {
  logical "$@" | awk '
    function emit() { sub(/^[ \t]+/, "", piece); sub(/[ \t]+$/, "", piece); if (piece != "") print head piece; piece = "" }
    {
      match($0, /^[^:]*:[0-9]+:/); head = substr($0, 1, RLENGTH); c = substr($0, RLENGTH + 1)
      if (c ~ /^(-[ \t]+)?name:/) { print; next }
      match(c, /^(-[ \t]+)?([A-Za-z_][A-Za-z0-9_-]*:[ \t]+)?/); key = substr(c, 1, RLENGTH); c = substr(c, RLENGTH + 1)
      q = substr(c, 1, 1)
      if (key != "" && (q == "\"" || q == "\047") && length(c) > 1 && substr(c, length(c)) == q) c = substr(c, 2, length(c) - 2)
      c = key c; piece = ""; q = ""; n = length(c)
      for (i = 1; i <= n; i++) {
        ch = substr(c, i, 1)
        if (q == "\047") { if (ch == q) q = ""; piece = piece ch; continue }
        if (ch == "\\") { piece = piece substr(c, i, 2); i++; continue }
        if (q == "\"") { if (ch == q) q = ""; piece = piece ch; continue }
        if (substr(c, i, 3) == "${{" && (j = index(substr(c, i), "}}")) > 0) { piece = piece substr(c, i, j + 1); i += j; continue }
        if (ch == "\"" || ch == "\047") q = ch
        else if (ch == ";" || ch == "|" || ch == "(" || ch == ")" || substr(c, i, 2) == "&&") { emit(); if (substr(c, i, 2) ~ /^(&&|[|][|])$/) i++; continue }
        piece = piece ch
      }
      emit()
    }'
}
# Single commands whose text (not file name, not a YAML step name) matches the ERE.
# Usage: scan ERE file...
scan() {
  local re=$1
  shift
  commands "$@" | RE=$re awk '{ c = $0; sub(/^[^:]*:[0-9]+:/, "", c)
    if (c !~ /^(-[ \t]+)?name:/ && c ~ ENVIRON["RE"]) print }'
}
loc() { local t=${1#*:}; printf '%s' "${1%%:*}:${t%%:*}"; }           # file:line from scan
text() { local t=${1#*:}; printf '%s' "${t#*:}"; }                   # command text from scan
# One npm install command's own ignore-scripts settings, as "FLAG|PREFIX", each
# true, false or empty (any case, quotes ignored).
#   FLAG    the last of --ignore-scripts[=true|false], --ignore-scripts true|false and
#           --no-ignore-scripts among its arguments, read left to right as npm does
#   PREFIX  a command-local npm_config_ignore_scripts=true|false before npm
npm_script_flags() {
  printf '%s\n' "$1" | awk '{
    t = tolower($0); gsub(/["\047]/, "", t)
    if (!match(t, /(^|[^[:alnum:]_.-])npm[[:space:]]+(ci|install|i)([[:space:]]|$)/)) exit
    pre = substr(t, 1, RSTART); n = split(substr(t, RSTART + RLENGTH), a, /[[:space:]]+/)
    flag = ""; pfx = ""
    for (i = 1; i <= n; i++) {
      if (a[i] == "--no-ignore-scripts") flag = "false"
      else if (a[i] ~ /^--ignore-scripts=(true|false)$/) flag = substr(a[i], 18)
      else if (a[i] == "--ignore-scripts") { if (a[i + 1] ~ /^(true|false)$/) flag = a[++i]; else flag = "true" }
    }
    m = split(pre, w, /[[:space:]]+/)
    for (i = 1; i <= m; i++) if (w[i] ~ /^npm_config_ignore_scripts=(true|false)$/) pfx = substr(w[i], 27)
    print flag "|" pfx }'
}
# npm_config_ignore_scripts from the YAML env: or variables: mapping nearest to
# line $2 of file $1 (step over job over workflow), as "true:N" or "false:N"
# where N is the line that sets it; nothing if no such mapping covers the line.
yaml_npm_env() {
  awk -v at="$2" '
    function ind(s) { match(s, /^[ \t]*/); return RLENGTH }
    function kind(s,   i) { i = ind(s); if (substr(s, i + 1, 2) ~ /^-[ \t]/) return i + 1 + ind(substr(s, i + 2)); return i }
    { sub(/\r$/, ""); t[NR] = $0; skip[NR] = ($0 ~ /^[ \t]*(#.*)?$/) }
    END {
      best = -1
      for (s = 1; s <= NR; s++) {
        low = tolower(t[s])
        if (skip[s] || low !~ /^[ \t]*["\047]?npm_config_ignore_scripts["\047]?[ \t]*:[ \t]*["\047]?(true|false)["\047]?[ \t]*(#.*)?$/) continue
        k = ind(t[s])
        for (p = s - 1; p >= 1 && (skip[p] || ind(t[p]) >= k); p--) ;
        if (p < 1 || t[p] !~ /^[ \t]*(-[ \t]+)?(env|variables)[ \t]*:[ \t]*(#.*)?$/) continue
        pk = kind(t[p]); a = p
        if (pk == ind(t[p])) { # walk back to the first key of the mapping that holds env:
          for (a = p - 1; a >= 1 && (skip[a] || ind(t[a]) >= pk); a--) ;
          if (a < 1 || kind(t[a]) != pk) a++
        }
        for (b = p + 1; b <= NR && (skip[b] || ind(t[b]) >= pk); b++) ;
        if (a <= at && at < b && pk >= best) { best = pk; v = (low ~ /true/) ? "true" : "false"; n = s }
      }
      if (best >= 0) print v ":" n
    }' "$1" 2>/dev/null
}
# Other npm_config_ignore_scripts settings in file $1 (export, a $GITHUB_ENV write,
# a bare assignment): not a YAML key and not one command's prefix, so their reach
# is not worked out. Prints "file:line:true|false" for each.
npm_env_unscoped() {
  commands "$1" | awk '{
    c = $0; sub(/^[^:]*:[0-9]+:/, "", c); h = substr($0, 1, length($0) - length(c))
    l = tolower(c); gsub(/["\047]/, "", l)
    if (!match(l, /npm_config_ignore_scripts[ \t]*[=:][ \t]*(true|false)/)) next
    v = (substr(l, RSTART, RLENGTH) ~ /true$/) ? "true" : "false"
    if (l ~ /^(-[ \t]+)?npm_config_ignore_scripts[ \t]*:/) next
    sub(/^(-[ \t]+)?([a-z_][a-z0-9_-]*:[ \t]+)?/, "", l)
    if (l ~ /^(env[ \t]+)?([a-z_][a-z0-9_]*=[^ \t]*[ \t]+)*npm_config_ignore_scripts=[^ \t]*[ \t]+([a-z_][a-z0-9_]*=[^ \t]*[ \t]+)*[^ \t=]/) next
    print h v }'
}
present() { # print the trigger files that exist
  local f out=""
  for f in "$@"; do [ -f "$f" ] && out="$out${out:+, }$f"; done
  printf '%s' "$out"
}

py_trigger=$(present pyproject.toml setup.py setup.cfg requirements.txt uv.lock poetry.lock)
conda_trigger=$(present pixi.toml pixi.lock environment.yml environment.yaml conda-lock.yml .condarc)
if [ -z "$conda_trigger" ] && grep -qE '^\[tool\.pixi' pyproject.toml 2>/dev/null; then
  conda_trigger="pyproject.toml [tool.pixi]"
fi
has_python=no; [ -n "$py_trigger" ] && has_python=yes
has_conda=no; [ -n "$conda_trigger" ] && has_conda=yes

# Each section prints a "detected" line when its trigger files exist. The CI
# command checks run regardless, so a crate or package in a subdirectory is
# still covered when CI builds it.

# --------------------------------------------------------------------- npm
npm_checks() {
  local pm=npm line installs_re='(^|[^[:alnum:]_.-])npm[[:space:]]+(ci|install|i)([[:space:]]|$)'
  if [ -f package.json ]; then
    say npm INFO "detected (package.json) -> references/npm-quirks.md"
    if [ -f package-lock.json ] || [ -f npm-shrinkwrap.json ]; then pm=npm
    elif [ -f pnpm-lock.yaml ]; then pm=pnpm
    elif [ -f yarn.lock ]; then pm=yarn
    else say npm FAIL "no lockfile committed (package-lock.json, npm-shrinkwrap.json, pnpm-lock.yaml or yarn.lock)"
    fi
  elif [ -z "$(scan "$installs_re" "${ci_files[@]}")" ]; then
    return 0
  fi
  if [ "$pm" != npm ]; then
    say npm INFO "$pm project: script policy and lockfile flags differ from npm; see the pnpm/Yarn section of references/npm-quirks.md"
    return 0
  fi

  # Lifecycle scripts: judge each CI install by its effective ignore-scripts value.
  # npm precedence: command line, then npm_config_ignore_scripts, then .npmrc. The
  # variable counts only as a prefix of that command or from a YAML env:/variables:
  # mapping over it; a setting whose reach is unknown turns the verdict into a WARN.
  local npmrc cli pre yaml eff other f found=no
  npmrc=$(awk -F= 'tolower($1) ~ /^[ \t]*ignore-scripts[ \t]*$/ { v = tolower($2); gsub(/[ \t"\047]/, "", v); last = v }
    END { print last }' .npmrc 2>/dev/null)
  while IFS= read -r line; do
    found=yes
    f=${line%%:*}
    IFS='|' read -r cli pre <<< "$(npm_script_flags "$(text "$line")")"
    if [ "$cli" = false ]; then
      say npm FAIL "lifecycle scripts re-enabled on the command line at $(loc "$line")"
    elif [ -z "$cli" ] && [ "$pre" = false ]; then
      say npm FAIL "npm_config_ignore_scripts=false on the command re-enables lifecycle scripts at $(loc "$line")"
    elif [ -z "$cli$pre" ]; then
      yaml=$(yaml_npm_env "$f" "$(printf '%s' "$line" | cut -d: -f2)")
      eff=${yaml%%:*}; [ -n "$yaml" ] || eff=$npmrc
      [ "$eff" = true ] || eff=false
      other=$(npm_env_unscoped "$f" | grep -v ":$eff\$" | head -1)
      if [ -n "$other" ] && [ "$eff" = true ]; then
        say npm WARN "cannot confirm lifecycle scripts are off at $(loc "$line"): npm_config_ignore_scripts=false at $(loc "$other") may reach it"
      elif [ -n "$other" ]; then
        say npm WARN "cannot confirm lifecycle scripts are off at $(loc "$line"): npm_config_ignore_scripts=true at $(loc "$other") may not reach it; add --ignore-scripts there"
      elif [ "$eff" = true ]; then
        :
      elif [ -n "$yaml" ]; then
        say npm FAIL "npm_config_ignore_scripts=false at $f:${yaml#*:} re-enables lifecycle scripts at $(loc "$line")"
      else
        say npm FAIL "dependency lifecycle scripts run at $(loc "$line"): add --ignore-scripts there or ignore-scripts=true to .npmrc"
      fi
    fi
  done < <(scan "$installs_re" "${ci_files[@]}")
  if [ $found = no ] && [ "$npmrc" != true ]; then
    say npm FAIL "no ignore-scripts=true in .npmrc and no CI install step with --ignore-scripts"
  fi

  # CI must install from the lockfile.
  while IFS= read -r line; do
    case $line in
      *" -g"*|*--global*) ;;
      *) say npm FAIL "CI runs 'npm install' at $(loc "$line"); use 'npm ci' so package-lock.json is enforced" ;;
    esac
  done < <(scan '(^|[^[:alnum:]_.-])npm[[:space:]]+(install|i)([[:space:]]|$)' "${ci_files[@]}")
}

# ------------------------------------------------------------------- PyPI
pypi_checks() {
  [ $has_python = yes ] && say pypi INFO "detected ($py_trigger) -> references/pypi-quirks.md"
  local line f key val
  # Command-line escape hatch in CI and build scripts.
  while IFS= read -r line; do
    say pypi FAIL "build isolation disabled at $(loc "$line"); build backends then run in the install environment"
  done < <(scan '(^|[[:space:]])--no-build-isolation([[:space:]=]|-package|$)' "${build_files[@]}")
  # uv/pixi TOML settings, judged by value: true or a non-empty package list disables
  # isolation; false and [] keep it.
  for f in pyproject.toml uv.toml pixi.toml; do
    [ -f "$f" ] || continue
    while IFS='|' read -r line key val; do
      case $val in
        true) say pypi FAIL "$key = true at $line; build isolation disabled for every package" ;;
        *\"*|*\'*) say pypi FAIL "$key = $val at $line; build isolation disabled for these packages" ;;
      esac
    done < <(awk '
      function clean(s) { sub(/[ \t]*#.*$/, "", s); sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }
      /^[ \t]*no-build-isolation(-package)?[ \t]*=/ {
        key = $0; sub(/[ \t]*=.*$/, "", key); sub(/^[ \t]+/, "", key)
        val = $0; sub(/^[^=]*=/, "", val); val = clean(val); n = FNR
        if (val ~ /^\[/) while (val !~ /\]/ && (getline more) > 0) val = val " " clean(more)
        print FILENAME ":" n "|" key "|" val
      }' "$f")
  done
  while IFS= read -r line; do
    say pypi WARN "custom build backend at $(loc "$line"); audit the backend code it points to"
  done < <(grep -nHE '^[[:space:]]*backend-path[[:space:]]*=' pyproject.toml 2>/dev/null)
}

# ------------------------------------------------------ Python .pth / .start
# Collect every site directory: interpreters on PATH (queried with -I -S, which
# skips .pth processing) plus environment prefixes found on disk (not executed).
site_dirs() {
  local py prefix d
  for py in python3 python; do
    command -v "$py" >/dev/null 2>&1 || continue
    "$py" -I -S -c '
import os, site, sys
pre = {sys.prefix, sys.exec_prefix,
       getattr(sys, "base_prefix", sys.prefix), getattr(sys, "base_exec_prefix", sys.exec_prefix)}
exe = os.path.abspath(sys.executable)
for cand in (os.path.dirname(exe), os.path.dirname(os.path.dirname(exe))):
    if os.path.isfile(os.path.join(cand, "pyvenv.cfg")):
        pre.add(cand)
print("\n".join(site.getsitepackages(sorted(pre)) + [site.getusersitepackages()]))
' 2>/dev/null
  done
  for prefix in "${VIRTUAL_ENV:-}" "${CONDA_PREFIX:-}" .venv venv .pixi/envs/* "${extra_envs[@]}"; do
    [ -n "$prefix" ] && [ -d "$prefix" ] || continue
    for d in "$prefix"/lib/python3*/site-packages "$prefix"/lib/pypy3*/site-packages "$prefix"/Lib/site-packages; do
      [ -d "$d" ] && printf '%s\n' "$d"
    done
  done
}

pth_scan() {
  local scanner="" py d listing dirs=()
  for py in python3 python; do
    command -v "$py" >/dev/null 2>&1 && { scanner=$py; break; }
  done
  if [ -z "$scanner" ]; then
    say pypi WARN "no python3/python on PATH to run the scan; .pth/.start scan skipped"
    return 0
  fi
  listing=$(site_dirs)
  while IFS= read -r d; do
    [ -n "$d" ] && [ -d "$d" ] && dirs+=("$(cd "$d" && pwd -P)")
  done <<< "$listing"
  if [ ${#dirs[@]} -eq 0 ]; then
    say pypi WARN "no Python site directories found; .pth/.start scan skipped"
    return 0
  fi
  # Known-good files must match the name and the exact code their tool writes, and
  # the .pth/.start file and the module it imports must belong to that tool.
  if ! "$scanner" -I -S - "${dirs[@]}" <<'PY'
import csv, glob, json, os, re, sys

VENV, EDITABLE = "venv", "editable"
KNOWN = [  # (file-name regex, regex every code line must fully match, origin, owner, module)
    # owner: the package that must install the file and the module it imports; EDITABLE =
    # one editable install; VENV = no package, in a venv uv or virtualenv created.
    # module: the module the code imports; None = group 1 of the line regex.
    (r"distutils-precedence\.pth",
     r"import os; (var = 'SETUPTOOLS_USE_DISTUTILS'; enabled = os\.environ\.get\(var, '(local|stdlib)'\)|"
     r"enabled = os\.environ\.get\('SETUPTOOLS_USE_DISTUTILS'\)) == 'local'; "
     r"enabled and __import__\('_distutils_hack'\)\.add_shim\(\);?", "setuptools >= 49.3 distutils shim",
     "setuptools", "_distutils_hack"),
    (r"_virtualenv\.pth", r"import _virtualenv", "uv venv, or virtualenv 20.x", VENV, "_virtualenv"),
    (r"__editable__\..+\.pth", r"import (__editable___\w+_finder); \1\.install\(\)", "setuptools editable install",
     EDITABLE, None),
    (r"_editable_impl_\w+\.pth", r"import (_editable_impl_\w+)", "editables-based editable install, e.g. hatchling dev-mode-exact",
     EDITABLE, None),
    (r"_editable_skbc_\w+\.pth", r"import (_editable_skbc_\w+)", "scikit-build-core editable install", EDITABLE, None),
    (r"_editable_skbc_\w+\.start", r"(_editable_skbc_\w+):entrypoint", "scikit-build-core editable install", EDITABLE, None),
    (r".+-editable\.pth", r"import (_\w+_editable_loader); \1\.init\(\)", "meson-python editable install", EDITABLE, None),
    (r".+-editable\.start", r"(_\w+_editable_loader):init", "meson-python editable install", EDITABLE, None),
    (r"a1_coverage\.pth",
     r"import sys; exec\('(\\n)*import os\\n\\nif os\.getenv\(\"COVERAGE_PROCESS_START\"\) or "
     r"os\.getenv\(\"COVERAGE_PROCESS_CONFIG\"\):\\n try:\\n  import coverage\\n except:\\n  pass\\n else:\\n  "
     r"coverage\.process_startup\(slug=\"pth\"\)(\\n)*'\)", "coverage >= 7.13 subprocess measurement",
     "coverage", "coverage"),
    (r"pytest-cov\.pth",
     re.escape("import os, sys;exec('if \\'COV_CORE_SOURCE\\' in os.environ:\\n try:\\n  from pytest_cov.embed "
               "import init\\n  init()\\n except Exception as exc:\\n  sys.stderr.write(\\n   \"pytest-cov: Failed "
               "to setup subprocess coverage. \"\\n   \"Environ: {0!r} \"\\n   \"Exception: {1!r}\\\\n\".format(\\n"
               "    dict((k, v) for k, v in os.environ.items() if k.startswith(\\'COV_CORE\\')),\\n    exc\\n   )\\n"
               "  )\\n')"), "pytest-cov < 7 subprocess support", "pytest_cov", "pytest_cov"),
]
# setuptools' *-nspkg.pth line templates (namespaces.py _nspkg_tmpl): 31.x, 36-69, 75+.
NSPKG_HEAD = "import sys, types, os;"
NSPKG_TMPLS = [
    "has_mfs = sys.version_info > (3, 5);p = os.path.join(%(root)s, *%(pth)r);"
    "importlib = has_mfs and __import__('importlib.util');has_mfs and __import__('importlib.machinery');"
    "m = has_mfs and sys.modules.setdefault(%(pkg)r, importlib.util.module_from_spec("
    "importlib.machinery.PathFinder.find_spec(%(pkg)r, [os.path.dirname(p)])));"
    "m = m or %(not_mfs)ssys.modules.setdefault(%(pkg)r, types.ModuleType(%(pkg)r));",
    "p = os.path.join(%(root)s, *%(pth)r);importlib = __import__('importlib.util');"
    "__import__('importlib.machinery');m = sys.modules.setdefault(%(pkg)r, importlib.util.module_from_spec("
    "importlib.machinery.PathFinder.find_spec(%(pkg)r, [os.path.dirname(p)])));"
    "m = m or sys.modules.setdefault(%(pkg)r, types.ModuleType(%(pkg)r));",
]
NSPKG_TAIL = "mp = (m or []) and m.__dict__.setdefault('__path__',[]);(p not in mp) and mp.append(p)"
NSPKG_MULTI = ";m and setattr(sys.modules[%(parent)r], %(child)r, m)"
NSPKG_PKG = re.compile(r"sys\.modules\.setdefault\('([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)'")


def nspkg_line(line):
    """True only if the line is exactly what setuptools writes for the namespace package it names."""
    m = NSPKG_PKG.search(line)
    if not m:
        return False
    pkg = m.group(1)
    parent, _, child = pkg.rpartition(".")
    values = dict(root="sys._getframe(1).f_locals['sitedir']", pth=tuple(pkg.split(".")),
                  pkg=pkg, parent=parent, child=child)
    for tmpl in NSPKG_TMPLS:
        for not_mfs in ("", "not has_mfs and "):
            text = NSPKG_HEAD + tmpl % dict(values, not_mfs=not_mfs) + NSPKG_TAIL
            if parent:
                text += NSPKG_MULTI % values
            if line == text:
                return True
    return False


def code_lines(path):
    """Lines CPython runs at startup: .pth 'import' lines (stripped, as 3.15 does) or any .start entry."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    out = []
    for line in text.splitlines():  # same splitting as site.py: \r, \x0c and friends end a line too
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if path.endswith(".start") or s.startswith(("import ", "import\t")):
            out.append(s)
    return out


def known(name, lines):
    """(origin, owner rule, imported module) for known-good code, else None. The
    namespace-package lines import no module, so they get no owner rule."""
    if name.endswith("-nspkg.pth") and all(nspkg_line(ln) for ln in lines):
        return "setuptools namespace package, e.g. matplotlib <= 3.7", None, None
    for name_re, line_re, origin, rule, module in KNOWN:
        if re.fullmatch(name_re, name) and all(re.fullmatch(line_re, ln) for ln in lines):
            return origin, rule, module or re.fullmatch(line_re, lines[0]).group(1)
    return None


def norm(dist):
    return re.sub(r"[-_.]+", "_", dist).lower()


def up(sitedir, test):
    """The nearest of the site dir's three parents for which test(dir) is true, or None."""
    d = sitedir
    for _ in range(3):
        d = os.path.dirname(d)
        if test(d):
            return d
    return None


FILES = {}


def files_of(sitedir):
    """Map each path under sitedir to the packages that installed it, from wheel RECORD
    files and, in a conda or pixi env, conda-meta (conda packages have no RECORD)."""
    if sitedir not in FILES:
        files = FILES[sitedir] = {}
        for record in glob.glob(os.path.join(sitedir, "*.dist-info", "RECORD")):
            dist = norm(os.path.basename(os.path.dirname(record))[: -len(".dist-info")].rpartition("-")[0])
            try:
                with open(record, newline="", encoding="utf-8") as f:
                    for row in csv.reader(f):
                        if row:
                            files.setdefault(row[0], set()).add(dist)
            except OSError:
                pass
        prefix = up(sitedir, lambda d: os.path.isdir(os.path.join(d, "conda-meta")))
        if prefix:
            rel = os.path.relpath(sitedir, prefix).replace(os.sep, "/") + "/"
            for meta in glob.glob(os.path.join(prefix, "conda-meta", "*.json")):
                try:
                    with open(meta, encoding="utf-8") as f:
                        pkg = json.load(f)
                except (OSError, ValueError):
                    continue
                for path in pkg.get("files", []):
                    if path.startswith(rel):
                        files.setdefault(path[len(rel):], set()).add(norm(pkg.get("name", "?")))
    return FILES[sitedir]


def owners(sitedir, name, module):
    """Packages that installed the file, and packages that installed the module it imports."""
    files = files_of(sitedir)
    mod = set()
    if module:
        for path, dists in files.items():
            head = path.split("/", 1)[0]
            if head.split(".", 1)[0] == module:  # module.py, module/..., module.<abi>.so
                mod |= dists
    return files.get(name, set()), mod


def project_name(src):
    """The project name a source tree declares without running code: [project] or
    [tool.poetry] name in pyproject.toml, or [metadata] name in setup.cfg. None if none."""
    try:
        with open(os.path.join(src, "pyproject.toml"), encoding="utf-8") as f:
            section = None
            for line in f:
                if re.match(r"\s*\[", line):
                    section = line.strip()
                m = re.match(r"""\s*name\s*=\s*["']([^"']+)["']""", line)
                if section in ("[project]", "[tool.poetry]") and m:
                    return m.group(1)
    except OSError:
        pass
    import configparser
    cfg = configparser.RawConfigParser()
    try:
        cfg.read(os.path.join(src, "setup.cfg"), encoding="utf-8")
        return cfg.get("metadata", "name").strip() or None
    except (configparser.Error, UnicodeDecodeError):
        return None


def editable(sitedir, dist):
    """None if dist is an editable install of its own source tree outside the environment,
    else (level, problem). A wheel from an index can ship its own direct_url.json, but it
    cannot create a project directory outside the environment (its data files land inside
    it) without already running code. The URL must be an absolute local path: an empty
    "file://" would resolve to the scanned project."""
    bad = ("FAIL", "file and the module it imports are not from one editable install of a source tree "
           "outside the environment (direct_url.json)")
    for info in glob.glob(os.path.join(sitedir, "*.dist-info")):
        if norm(os.path.basename(info)[: -len(".dist-info")].rpartition("-")[0]) != dist:
            continue
        try:
            with open(os.path.join(info, "direct_url.json"), encoding="utf-8") as f:
                direct = json.load(f)
            url = direct["url"]
            if direct.get("dir_info", {}).get("editable") is not True or not url.startswith("file://"):
                return bad
        except (OSError, ValueError, AttributeError, KeyError, TypeError):
            return bad
        from urllib.parse import urlparse, unquote
        from urllib.request import url2pathname
        parsed = urlparse(url)
        path = url2pathname(unquote(parsed.path))
        if parsed.netloc not in ("", "localhost") or not os.path.isabs(path):
            return bad
        src = os.path.realpath(path)
        env = up(sitedir, lambda d: any(os.path.exists(os.path.join(d, m)) for m in ("pyvenv.cfg", "conda-meta")))
        env = os.path.realpath(env or os.path.dirname(os.path.dirname(os.path.dirname(sitedir))))
        if not os.path.isdir(src) or os.path.commonpath([src, env]) == env:
            return bad
        if not any(os.path.isfile(os.path.join(src, n)) for n in ("pyproject.toml", "setup.py", "setup.cfg")):
            return bad
        name = project_name(src)
        if name is None:
            return ("WARN", "its source tree %s declares no project name (setup.py only?), so it can't be "
                    "confirmed as %s's; check direct_url.json and the tree by hand" % (src, dist))
        if norm(name) != dist:
            return ("FAIL", "direct_url.json points to %s, whose project is %s, not %s" % (src, name, dist))
        return None
    return bad


def venv_by_tool(sitedir):
    """True if the site dir is in a venv whose pyvenv.cfg has a uv or virtualenv key."""
    prefix = up(sitedir, lambda d: os.path.isfile(os.path.join(d, "pyvenv.cfg")))
    if not prefix:
        return False
    try:
        with open(os.path.join(prefix, "pyvenv.cfg"), encoding="utf-8") as f:
            return any(ln.partition("=")[0].strip().lower() in ("uv", "virtualenv") for ln in f if "=" in ln)
    except OSError:
        return False


def judge(sitedir, name, rule, module):
    """(level, problem, owner text) for a file whose name and code are known-good."""
    pth, mod = owners(sitedir, name, module)
    who = ", ".join(sorted(pth | mod)) or "none recorded"
    if rule is None:
        return "INFO", "", who
    if rule == VENV:
        if pth or mod:
            return "FAIL", "installed by a package, not by uv or virtualenv", who
        if not venv_by_tool(sitedir):
            return "FAIL", "not in a venv whose pyvenv.cfg names uv or virtualenv", who
        return "INFO", "", who
    if rule == EDITABLE:
        if len(pth) != 1 or mod != pth:
            return "FAIL", "file and %s are not from one editable install" % module, who
        problem = editable(sitedir, next(iter(pth)))
        if problem:
            return problem[0], problem[1], who
        return "INFO", "", who
    if not pth and not mod:
        return "WARN", "no RECORD or conda-meta names its owner; confirm it with the package manager that installed %s" % rule, who
    if pth != {rule} or mod != {rule}:
        return "FAIL", "file and %s must both belong to %s only" % (module, rule), who
    return "INFO", "", who


fails = 0
for sitedir in dict.fromkeys(sys.argv[1:]):
    try:
        names = sorted(n for n in os.listdir(sitedir) if n.endswith((".pth", ".start")))
    except OSError as exc:
        print("pypi WARN: cannot list %s: %s" % (sitedir, exc))
        continue
    print("pypi INFO: scanned %d .pth/.start files in %s" % (len(names), sitedir))
    for name in names:
        path = os.path.join(sitedir, name)
        try:
            lines = code_lines(path)
        except OSError as exc:
            print("pypi WARN: cannot read %s: %s" % (path, exc))
            continue
        if not lines:
            continue  # path entries only
        match = known(name, lines)
        if match:
            origin, rule, module = match
            level, problem, who = judge(sitedir, name, rule, module)
            if level == "INFO":
                print("pypi INFO: known startup code in %s: %s (owner: %s)" % (path, origin, who))
            else:
                fails += level == "FAIL"
                print("pypi %s: startup code in %s looks like %s, but %s (owner: %s)" % (level, path, origin, problem, who))
        else:
            fails += 1
            print("pypi FAIL: unknown startup code in %s (owner: %s): %s"
                  % (path, ", ".join(sorted(owners(sitedir, name, None)[0])) or "none recorded", lines[0][:160]))
sys.exit(1 if fails else 0)
PY
  then
    fails=$((fails + 1))
  fi
}

# ------------------------------------------------------------ conda / pixi
conda_checks() {
  [ $has_conda = yes ] && say conda INFO "detected ($conda_trigger) -> references/conda-pixi-quirks.md"
  local tok='(^|[^[:alnum:]_./-])defaults([^[:alnum:]_./-]|$)|repo[.]anaconda[.]com/pkgs' line f
  # YAML: entries under the top-level channels: key (block or flow style).
  for f in environment.yml environment.yaml .condarc; do
    [ -f "$f" ] || continue
    while IFS= read -r line; do
      say conda WARN "Anaconda 'defaults' channel at $line; prefer conda-forge"
    done < <(awk -v tok="$tok" '
      /^[^[:space:]#-][^:]*:/ { inch = ($0 ~ /^channels[[:space:]]*:/) }
      inch && $0 !~ /^[[:space:]]*#/ && $0 ~ tok { print FILENAME ":" FNR }' "$f")
  done
  # TOML: channels = [ ... ] arrays in pixi.toml or [tool.pixi.*] in pyproject.toml.
  for f in pixi.toml pyproject.toml; do
    [ -f "$f" ] || continue
    while IFS= read -r line; do
      say conda WARN "Anaconda 'defaults' channel at $line; prefer conda-forge (pixi has no 'defaults' alias)"
    done < <(awk -v tok="$tok" '
      /^[[:space:]]*channels[[:space:]]*=/ { inch = 1 }
      inch && $0 !~ /^[[:space:]]*#/ && $0 ~ tok { print FILENAME ":" FNR }
      inch && /\]/ { inch = 0 }' "$f")
  done
  while IFS= read -r line; do
    say conda FAIL "solver/lockfile escape hatch at $(loc "$line")"
  done < <(scan '(^|[^[:alnum:]_.-])(conda|mamba|micromamba)[[:space:]]+(install|update|create)[[:space:]].*(--no-deps|--no-pin|--force-reinstall)' "${build_files[@]}")
}

# ------------------------------------------------------------------ cargo
cargo_checks() {
  local line manifest
  # Rust extensions of Python packages often keep Cargo.toml in a subdirectory.
  manifest=$(find . -maxdepth 3 -name Cargo.toml -not -path '*/target/*' -not -path './.pixi/*' \
    -not -path '*/node_modules/*' 2>/dev/null | head -1)
  if [ -n "$manifest" ]; then
    say cargo INFO "detected (${manifest#./}) -> references/cargo-go-quirks.md"
    while IFS= read -r line; do
      say cargo INFO "build.rs present (runs at every build): ${line#./}"
    done < <(find . -name build.rs -not -path '*/target/*' -not -path './.pixi/*' \
      -not -path '*/node_modules/*' 2>/dev/null | head -5)
  fi
  while IFS= read -r line; do
    case $line in
      *--locked*|*--frozen*) ;;
      *) say cargo FAIL "cargo without --locked at $(loc "$line"); Cargo.lock can be rewritten silently" ;;
    esac
  done < <(scan '(^|[^[:alnum:]_.-])cargo[[:space:]]+(\+[^[:space:]]+[[:space:]]+)?(build|test|run)([[:space:]]|$)' "${ci_files[@]}")
}

# --------------------------------------------------------------------- Go
go_checks() {
  local line v
  [ -f go.mod ] && say go INFO "detected (go.mod) -> references/cargo-go-quirks.md"
  if [ -f go.mod ] && command -v go >/dev/null 2>&1; then
    # Run outside the project so a go.mod toolchain line cannot trigger a toolchain download.
    v=$(cd / && go env GOSUMDB 2>/dev/null)
    [ "$v" = off ] && say go FAIL "GOSUMDB=off in the local go env; checksum database not consulted"
    v=$(cd / && go env GOFLAGS 2>/dev/null)
    case $v in *-mod=mod*) say go WARN "GOFLAGS contains -mod=mod in the local go env; go commands may rewrite go.mod/go.sum" ;; esac
  fi
  while IFS= read -r line; do
    say go FAIL "GOSUMDB=off at $(loc "$line"); checksum database not consulted"
  done < <(scan "GOSUMDB[\"']?[[:space:]]*[:=][[:space:]]*[\"']?off([\"'[:space:]]|$)" "${ci_files[@]}")
  # -mod=readonly is already the default since Go 1.16; only an explicit -mod=mod weakens it.
  while IFS= read -r line; do
    say go WARN "-mod=mod at $(loc "$line"); go commands may rewrite go.mod/go.sum"
  done < <(scan '-mod[=[:space:]]+mod([^[:alnum:]_]|$)' "${ci_files[@]}")
}

if [ $pth_only = yes ]; then
  pth_scan
else
  npm_checks
  pypi_checks
  { [ $has_python = yes ] || [ $has_conda = yes ] || [ ${#extra_envs[@]} -gt 0 ]; } && pth_scan
  conda_checks
  cargo_checks
  go_checks
fi
[ $fails -eq 0 ]
