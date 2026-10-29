"""English text for the unchanged target BFont (ASCII advance 6px, 11px glyphs)."""
import re

COLORS = "&|${}'\"`^<["
PLACEHOLDERS = re.compile(r'#[0-9]{1,2}|%[0-9]*[ds]')


def english_without_apostrophes(text):
    # The original engine treats ASCII apostrophe as a yellow color control.
    # Spell contractions out rather than changing the native escape table.
    special = {"can't":"cannot", "won't":"will not", "shan't":"shall not",
               "let's":"let us", "ain't":"is not", "i'm":"I am"}
    def replace(match):
        word = match.group(); lower = word.lower()
        if lower in special:
            result = special[lower]
            return result[0].upper() + result[1:] if word[0].isupper() else result
        for suffix, expansion in (("n't",' not'),("'re",' are'),("'ve",' have'),("'ll",' will'),("'d",' would')):
            if lower.endswith(suffix):
                return word[:-len(suffix)] + expansion
        if lower.endswith("'s"):
            stem = word[:-2]
            if stem.lower() in ('it','that','there','what','who','here','how','where','he','she','someone','something'):
                return stem + ' is'
            return stem  # concise compound names: Tyr Sword, Rufus Armor
        return word.replace("'", '')
    result = re.sub(r"\b[A-Za-z]+(?:'[A-Za-z]+)+", replace, text)
    result = re.sub(r'\b(He|She|It|There|Who|he|she|it|there|who) is (?=been|got|found|seen|done|gone|taken|left|lost|made|heard|become|returned|come)', r'\1 has ', result)
    result = result.replace('would better', 'had better')
    result = result.replace("'", '')
    return result


def visible_width(text):
    return sum(0 if ch in COLORS else (10 if ord(ch) > 127 else 6) for ch in text.lstrip(' ').split(';')[0].split('\0')[0])


def line_bytes(raw, width):
    """Original GetByteLenPrintable, one line, 5px ASCII / 9px Hangul + 1px gap."""
    position = used = 0
    while position < len(raw):
        byte = raw[position]
        if byte == 0:
            break
        if byte == 32 and used == 0:
            position += 1; continue
        if byte == 59:
            return position + 1
        if byte < 128 and chr(byte) in COLORS:
            position += 1; continue
        pixels = 10 if byte & 128 else 6
        if used + pixels > width:
            break
        position += 2 if byte & 128 else 1
        used += pixels
    return position


def native_lines(text,width):
    raw=text.encode('cp949').split(b'\0')[0];result=[]
    while raw:
        count=line_bytes(raw,width)
        if not count:raise ValueError('Font layout made no progress')
        result.append(raw[:count].decode('cp949'));raw=raw[count:]
    return result


def wrap_words(text, width):
    lines = []
    for paragraph in text.split(';'):
        words = paragraph.split(' '); line = ''
        for word in words:
            if not word:
                continue
            candidate = line + (' ' if line else '') + word
            if line and visible_width(candidate) > width:
                lines.append(line); line = word
            else:
                line = candidate
        lines.append(line)
    return ';'.join(lines)


def reflow(text, width):
    # The reference already hard-wraps at its old box width. Reflow ordinary
    # lines, retain paragraph breaks, then wrap for the unchanged target font.
    paragraphs=[]
    for part in text.split(';;'):
        sections=re.split(r';(?=\{Related Traits\||#0[123](?![0-9]))',part)
        paragraphs.append(';'.join(wrap_words(' '.join(section.replace(';',' ').split()),width)
                                   for section in sections))
    return ';;'.join(paragraphs)


def flowing_dialogue(text):
    """Leave line width to the current native dialog box, retaining paragraphs."""
    return ';;'.join(' '.join(part.replace(';',' ').split()) for part in text.split(';;'))


def context_limits(path, field, source, reference_limit):
    """Conservative boxes; keep runtime font size/spacing and original formats."""
    name = path.split('/')[-1]
    if path.endswith('.scn'):
        return (51, None) if field == 'title' else (min(reference_limit, 512), 220 if path.startswith('c/ep/') else 360)
    if field == 'name':
        if name == 'mission_list.dat':
            return 254, 150
        return 19, 114
    if field in ('title','category') and name.startswith('quest_'):
        return 27, 156
    if name.startswith('help_'):
        return (254, 126) if field == 'title' else (32766, 126)
    if field == 'description':
        return (199, 138) if name.startswith('quest_') else (254, 126)
    return 254, 156 if name=='menu_text.dat' else (336 if name=='tips.dat' else 126)
