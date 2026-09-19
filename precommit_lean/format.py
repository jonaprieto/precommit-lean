"""Reformat Lean 4 declaration headers to the diff-minimizing layout.

The layout is documented in .claude/commands/lean-format.md. This module implements
the mechanical part of it: attributes and modifiers above the keyword line, keyword
and name alone, one binder group per line at indent 4, a leading colon, the ascribed
type broken at every top-level operator, and the assignment on its own line.

It never changes a declaration whose entire text fits on one line, never joins lines,
never widens a line past 100 columns, and refuses any rewrite whose whitespace-stripped
text differs from the original. Anything it cannot parse confidently it leaves alone.
"""

import re
import sys

import pathlib

OPEN, CLOSE = '([{⟨⦃', ')]}⟩⦄'
MODS = ('private', 'protected', 'noncomputable', 'partial', 'unsafe', 'scoped', 'local')
KEYS = ('def', 'theorem', 'lemma', 'abbrev', 'instance', 'structure', 'inductive', 'class', 'example', 'opaque')
ATTR = re.compile(r'^((?:@\[[^\]]*\]\s*)+)(.*)$')
START = re.compile(rf'^(?:@\[[^\]]*\]\s*)*(?:(?:{"|".join(MODS)}) )*(?:{"|".join(KEYS)})\b')
DECL = re.compile(rf'^((?:(?:{"|".join(MODS)}) )*)({"|".join(KEYS)})\b(.*)$')
MARK = '→∧∨↔'

def depth_scan(s, d=0):
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '-' and s[i:i+2] == '--':
            break
        if ch == '"':                       # skip string literals
            i += 1
            while i < len(s) and s[i] != '"':
                i += 2 if s[i] == '\\' else 1
        elif ch in OPEN: d += 1
        elif ch in CLOSE: d -= 1
        i += 1
    return d

def header_end(lines, start):
    """index of the last header line, or None when this declaration is left alone"""
    d = 0
    for k in range(start, min(start + 40, len(lines))):
        line = lines[k]
        if k > start:
            stripped = line.lstrip()
            if not stripped or (d == 0 and ((stripped.startswith('|') and not stripped.startswith('|>'))
                                            or stripped.startswith('deriving'))):
                return k - 1
            if d == 0 and len(line) - len(stripped) == 0 and not stripped.startswith(('(', '{', '[', ':', 'extends')):
                return k - 1
        d0 = d
        d = depth_scan(line, d)
        text = re.sub(r'--.*$', '', line).rstrip()
        if d == 0 and (re.search(r'(^|\s)(:=|where|by|do)$', text)):
            if re.search(r'(^|\s)(let|have|fun|match)(\s|$)', text):
                return None                  # a local binding closes the line, not the header
            return k
        mm = re.search(r':=\s+\S', text)
        if mm and depth_scan(text[:mm.start()], d0) == 0:
            if re.search(r'(^|\s)(let|have|fun|match)(\s|$)', text[:mm.start()]):
                return None                  # that `:=` binds a local, not the declaration
            return k
    return None


def last_top_level_assign(s):
    """index of the last depth-0 `:=` in s, or None; string literals are skipped"""
    d = 0; i = 0; found = None
    while i < len(s):
        ch = s[i]
        if ch == '-' and s[i:i+2] == '--':
            break
        if ch == '"':
            i += 1
            while i < len(s) and s[i] != '"':
                i += 2 if s[i] == '\\' else 1
            i += 1
            continue
        if ch in OPEN: d += 1
        elif ch in CLOSE: d -= 1
        elif d == 0 and s[i:i+2] == ':=':
            found = i
            i += 2
            continue
        i += 1
    return found

def split_header(h, multiline=False):
    """(attrs, modifiers, keyword, name, binders, extends, type, tail) or None"""
    attrs = []
    ma = ATTR.match(h)
    if ma:
        attrs = re.findall(r'@\[[^\]]*\]', ma.group(1))
        h = ma.group(2)
    m = DECL.match(h)
    if not m:
        return None
    mods = m.group(1).split()
    key = m.group(2)
    rest = m.group(3).strip()
    tail = ''
    for suffix in (':= by', ':= do', ':=', 'where'):
        if rest.endswith(suffix) and depth_scan(rest[:len(rest) - len(suffix)]) == 0:
            tail = suffix
            rest = rest[:len(rest) - len(suffix)].rstrip()
            break
    else:
        pos = last_top_level_assign(rest)
        if pos is not None and rest[pos+2:].strip():
            if not multiline:
                return None                  # the whole declaration is one line: left alone
            head = rest[:pos]
            if re.search(r'(^|\s)(let|have|fun|do|match|if|then|else|where|by)(\s|$)', head):
                return None                  # that `:=` belongs to a binding inside the statement
            tail = rest[pos:].strip()        # body trails a multi-line header: it moves down
            rest = head.rstrip()
    # name
    if key == 'example' or (key == 'instance' and rest[:1] in (':', '(', '[', '{')):
        name = ''
    else:
        mn = re.match(r'(«[^»]+»|[^\s({\[⦃:]+)', rest)
        if not mn:
            return None
        name = mn.group(1)
        rest = rest[mn.end():].lstrip()
    binders, ext, ty = [], '', ''
    while rest:
        if rest.startswith('extends'):
            i = len(rest)
            d = 0
            for j, ch in enumerate(rest):
                if ch in OPEN: d += 1
                elif ch in CLOSE: d -= 1
                elif ch == ':' and d == 0:
                    i = j
                    break
            ext, rest = rest[:i].strip(), rest[i:].lstrip()
            continue
        if rest[0] == ':':
            ty = rest[1:].strip()
            break
        if rest[0] in OPEN:
            d = 0
            for j, ch in enumerate(rest):
                if ch in OPEN: d += 1
                elif ch in CLOSE:
                    d -= 1
                    if d == 0:
                        binders.append(rest[:j+1].strip())
                        rest = rest[j+1:].lstrip()
                        break
            else:
                return None
            continue
        return None                          # something unparsed: leave the declaration alone
    return attrs, mods, key, name, binders, ext, ty, tail

def split_type(ty):
    d = 0; out = []; prev = 0; i = 0
    while i < len(ty):
        ch = ty[i]
        if ch == '-' and ty[i:i+2] == '--':
            break
        if ch == '"':
            i += 1
            while i < len(ty) and ty[i] != '"':
                i += 2 if ty[i] == '\\' else 1
            i += 1
            continue
        if ch in OPEN: d += 1
        elif ch in CLOSE: d -= 1
        elif d == 0 and ch == '-' and ty[i+1:i+2] == '>':
            out.append(ty[prev:i+2].strip()); prev = i + 2; i += 1
        elif d == 0 and (ch in MARK or (ch == ',' and re.search(r'[∀∃]', ty[:i]))):
            out.append(ty[prev:i+1].strip()); prev = i + 1
        i += 1
    rest = ty[prev:].strip()
    if rest:
        out.append(rest)
    return out or ['']

def emit(parsed):
    attrs, mods, key, name, binders, ext, ty, tail = parsed
    out = list(attrs) + list(mods)
    out.append(f'{key} {name}'.strip())
    out += ['    ' + b for b in binders]
    if ext:
        out.append('    ' + ext)
    if ty:
        pieces = split_type(ty)
        out.append('    : ' + pieces[0])
        out += ['      ' + p for p in pieces[1:]]
        if tail == 'where':
            out.append('    where')
        elif tail:
            out.append('    ' + tail)
    else:
        if tail == 'where':
            out.append('    where')
        elif tail:
            out.append('    ' + tail)
    return out

def inert_spans(lines):
    """line indices inside a block comment, docstring, or multi-line string literal"""
    inert = set()
    depth = 0
    in_string = False
    for k, line in enumerate(lines):
        if depth or in_string:
            inert.add(k)
        j = 0
        while j < len(line):
            two = line[j:j+2]
            if not in_string and two == '/-':
                depth += 1; j += 2; continue
            if not in_string and two == '-/':
                depth = max(0, depth - 1); j += 2; continue
            if not depth and not in_string and two == '--':
                break
            if not depth and line[j] == '"' and not (j and line[j-1] == "'" and line[j+1:j+2] == "'"):
                in_string = not in_string
                j += 1
                continue
            if in_string and line[j] == '\\':
                j += 2; continue
            j += 1
        if depth or in_string:
            inert.add(k)
    return inert


def emit_keeping_type_lines(parsed, original):
    """Emit a declaration whose type has no operator to split at, keeping the author's
    own line breaks inside the type rather than joining it onto one over-long line."""
    attrs, mods, key, name, binders, ext, ty, tail = parsed
    joined = ' '.join(l.strip() for l in original)
    # locate the ascription colon in the original lines
    for k, line in enumerate(original):
        d = 0
        for j, ch in enumerate(line):
            if ch in OPEN: d += 1
            elif ch in CLOSE: d -= 1
            elif ch == ':' and d == 0 and line[j:j+2] != ':=':
                rest = line[j+1:].strip()
                chunks = ([rest] if rest else []) + [l.rstrip() for l in original[k+1:]]
                if not chunks:
                    return None
                if tail:
                    last = chunks[-1]
                    if last.endswith(tail):
                        chunks[-1] = last[:-len(tail)].rstrip()
                    if not chunks[-1]:
                        chunks.pop()
                base = None
                out = list(attrs) + list(mods) + [f'{key} {name}'.strip()]
                out += ['    ' + b for b in binders]
                if ext:
                    out.append('    ' + ext)
                for idx, c in enumerate(chunks):
                    if idx == 0:
                        out.append('    : ' + c.strip())
                    else:
                        ind = len(c) - len(c.lstrip())
                        if base is None:
                            base = ind
                        out.append(' ' * (6 + max(0, ind - base)) + c.strip())
                if tail:
                    out.append('    ' + tail)
                return out
    return None

def convert_text(text):
    lines = text.split('\n')
    inert = inert_spans(lines)
    out = []; i = 0; n = 0
    while i < len(lines):
        if i in inert or not START.match(lines[i]):
            out.append(lines[i]); i += 1; continue
        end = header_end(lines, i)
        if end is None or end < i:
            out.append(lines[i]); i += 1; continue
        header = ' '.join(l.strip() for l in lines[i:end+1])
        if '--' in header or '/-' in header:
            out.extend(lines[i:end+1]); i = end + 1; continue
        parsed = split_header(header, multiline=(end > i))
        if not parsed or (not parsed[4] and not parsed[6]):
            out.extend(lines[i:end+1]); i = end + 1; continue
        new = emit(parsed)
        if ''.join(''.join(new).split()) != ''.join(''.join(lines[i:end+1]).split()):
            out.extend(lines[i:end+1]); i = end + 1; continue   # never risk a token change
        if len(new) < end - i + 1:
            out.extend(lines[i:end+1]); i = end + 1; continue     # never join lines
        original = lines[i:end+1]
        if max(map(len, new)) > 100 >= max(map(len, original)):
            wrapped = emit_keeping_type_lines(parsed, original)
            if (wrapped and max(map(len, wrapped)) <= 100
                    and len(wrapped) >= len(original)
                    and ''.join(''.join(wrapped).split()) == ''.join(''.join(original).split())):
                out.extend(wrapped); n += 1; i = end + 1; continue
            out.extend(original); i = end + 1; continue           # never widen past the wrap column
        out.extend(new); n += 1; i = end + 1
    return '\n'.join(out), n


def check(paths, fix=False):
    """Return the list of paths that are not in the layout, rewriting them when fix."""
    offenders = []
    for name in paths:
        path = pathlib.Path(name)
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        formatted, _ = convert_text(text)
        if formatted == text:
            continue
        offenders.append(name)
        if fix:
            path.write_text(formatted)
    return offenders


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("filenames", nargs="*")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite the files instead of only reporting them",
    )
    arguments = parser.parse_args()

    offenders = check(arguments.filenames, fix=arguments.fix)
    if not offenders:
        return 0
    verb = "reformatted" if arguments.fix else "needs the signature layout"
    for name in offenders:
        print(f"{name}: {verb}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
