-- zenwritten (zenbones dark) theme for vis
-- Palette resolved from the Neovim zenwritten dark colorscheme.
-- Colors are literals on purpose: vis reloads themes with package.loaded[..]=nil.

local lexers = vis.lexers

local c = {
	bg      = '#191919',
	bg_cul  = '#222222',
	bg_nc   = '#242424',
	bg_pop  = '#2C2C2C',
	bg_stat = '#303030',
	bg_sel  = '#444444',
	bg_vis  = '#404040',
	fg      = '#BBBBBB',
	gray0   = '#686868',
	gray1   = '#616161',
	gray2   = '#555555',
	gray3   = '#8B8B8B',
	gray4   = '#939393',
	gray5   = '#969696',
	gray6   = '#9E9E9E',
	gray7   = '#CFCFCF',
	red     = '#DE6E7C',
	orange  = '#B77E64',
	green   = '#819B69',
	water   = '#6099C0',
	blossom = '#B279A7',
	teal    = '#66A5AD',
	search  = '#65435E',
}

local function fg(color, attr)
	return 'fore:' .. color .. (attr and ',' .. attr or '')
end

local function back(color, attr)
	return 'back:' .. color .. (attr and ',' .. attr or '')
end

local function both(f, b, attr)
	return fg(f) .. ',' .. back(b) .. (attr and ',' .. attr or '')
end

-- core lexer styles

lexers.STYLE_DEFAULT      = both(c.fg, c.bg)
lexers.STYLE_NOTHING      = ''
lexers.STYLE_WHITESPACE   = fg(c.gray2)
lexers.STYLE_COMMENT      = fg(c.gray0, 'italics')
lexers.STYLE_CONSTANT     = fg(c.gray3, 'italics')
lexers.STYLE_STRING       = fg(c.gray3, 'italics')
lexers.STYLE_NUMBER       = fg(c.gray3)
lexers.STYLE_KEYWORD      = fg(c.fg, 'bold')
lexers.STYLE_IDENTIFIER   = fg(c.gray6)
lexers.STYLE_OPERATOR     = fg(c.fg, 'bold')
lexers.STYLE_ERROR        = fg(c.red)
lexers.STYLE_PREPROCESSOR = fg(c.fg, 'bold')
lexers.STYLE_VARIABLE     = fg(c.gray6)
lexers.STYLE_FUNCTION     = fg(c.fg)
lexers.STYLE_CLASS        = fg(c.gray5, 'bold')
lexers.STYLE_TYPE         = fg(c.gray5)
lexers.STYLE_LABEL        = fg(c.blossom)
lexers.STYLE_REGEX        = fg(c.teal)
lexers.STYLE_EMBEDDED     = both(c.fg, c.bg_cul)
lexers.STYLE_TAG          = fg(c.blossom)
lexers.STYLE_ATTRIBUTE    = fg(c.water)
lexers.STYLE_HEADING      = fg(c.water, 'bold')
lexers.STYLE_BOLD         = 'bold'
lexers.STYLE_ITALIC       = 'italics'
lexers.STYLE_UNDERLINE    = 'underlined'
lexers.STYLE_CODE         = fg(c.blossom)
lexers.STYLE_LINK         = fg(c.water, 'underlined')
lexers.STYLE_REFERENCE    = fg(c.water)
lexers.STYLE_ANNOTATION   = fg(c.orange)
lexers.STYLE_LIST         = fg(c.blossom)
lexers.STYLE_DEFINITION   = fg(c.fg, 'bold')

lexers.STYLE_FUNCTION_BUILTIN = fg(c.teal)
lexers.STYLE_CONSTANT_BUILTIN = fg(c.blossom)
lexers.STYLE_FUNCTION_METHOD  = fg(c.fg)
lexers.STYLE_VARIABLE_BUILTIN = fg(c.orange)

-- UI styles

lexers.STYLE_LINENUMBER        = fg(c.gray1)
lexers.STYLE_LINENUMBER_CURSOR = fg(c.fg, 'bold')
lexers.STYLE_CURSOR            = 'reverse,keep_attribute'
lexers.STYLE_CURSOR_PRIMARY    = lexers.STYLE_CURSOR
lexers.STYLE_CURSOR_LINE       = back(c.bg_cul, 'keep_attribute')
lexers.STYLE_COLOR_COLUMN      = back(c.bg_pop)
lexers.STYLE_SELECTION         = back(c.bg_vis, 'keep_attribute')
lexers.STYLE_STATUS            = both(c.gray7, c.bg_nc)
lexers.STYLE_STATUS_FOCUSED    = both(c.fg, c.bg_stat)
lexers.STYLE_SEPARATOR         = both(c.gray1, c.bg_nc)
lexers.STYLE_INFO              = fg(c.fg, 'bold')
lexers.STYLE_EOF               = fg(c.gray2)

-- lexer specific

-- Diff
lexers.STYLE_ADDITION = fg(c.green)
lexers.STYLE_DELETION = fg(c.red)
lexers.STYLE_CHANGE   = fg(c.water)

-- CSS
lexers.STYLE_PROPERTY      = lexers.STYLE_ATTRIBUTE
lexers.STYLE_PSEUDOCLASS   = ''
lexers.STYLE_PSEUDOELEMENT = ''

-- HTML
lexers.STYLE_TAG_UNKNOWN       = lexers.STYLE_TAG .. ',italics'
lexers.STYLE_TAG_SINGLE        = lexers.STYLE_TAG
lexers.STYLE_TAG_DOCTYPE       = lexers.STYLE_TAG .. ',bold'
lexers.STYLE_ATTRIBUTE_UNKNOWN = lexers.STYLE_ATTRIBUTE .. ',italics'

-- LaTeX / TeX
lexers.STYLE_COMMAND            = lexers.STYLE_KEYWORD
lexers.STYLE_COMMAND_SECTION    = lexers.STYLE_CLASS
lexers.STYLE_ENVIRONMENT        = lexers.STYLE_TYPE
lexers.STYLE_ENVIRONMENT_MATH   = lexers.STYLE_NUMBER

-- Makefile
lexers.STYLE_TARGET = ''

-- Markdown
lexers.STYLE_HR = fg(c.gray1)
for i = 1, 6 do lexers['STYLE_HEADING_H' .. i] = lexers.STYLE_HEADING end
lexers.STYLE_BOLD      = 'bold'
lexers.STYLE_ITALIC    = 'italics'
lexers.STYLE_LIST      = lexers.STYLE_KEYWORD
lexers.STYLE_LINK      = lexers.STYLE_KEYWORD
lexers.STYLE_REFERENCE = lexers.STYLE_KEYWORD
lexers.STYLE_CODE      = lexers.STYLE_EMBEDDED

-- Output
lexers.STYLE_FILENAME = ''
lexers.STYLE_LINE     = ''
lexers.STYLE_COLUMN   = ''
lexers.STYLE_MESSAGE  = ''

-- Python
lexers.STYLE_KEYWORD_SOFT = ''

-- Taskpaper
lexers.STYLE_NOTE         = ''
lexers.STYLE_TAG_EXTENDED = ''
lexers.STYLE_TAG_DAY      = fg(c.blossom)
lexers.STYLE_TAG_OVERDUE  = fg(c.red)
lexers.STYLE_TAG_PLAIN    = ''

-- XML
lexers.STYLE_CDATA = ''

-- YAML
lexers.STYLE_ERROR_INDENT = back(c.red)

-- legacy lexers

-- Antlr
lexers.STYLE_ACTION = ''

-- Clojure
lexers.STYLE_CLOJURE_KEYWORD = lexers.STYLE_TYPE
lexers.STYLE_CLOJURE_SYMBOL  = lexers.STYLE_TYPE .. ',bold'

-- Gleam
lexers.STYLE_MODULE = lexers.STYLE_CONSTANT
lexers.STYLE_DISCARD = lexers.STYLE_COMMENT

-- Icon
lexers.STYLE_SPECIAL_KEYWORD = lexers.STYLE_TYPE

-- jq
lexers.STYLE_FORMAT = lexers.STYLE_CONSTANT
lexers.STYLE_SYSVAR = lexers.STYLE_CONSTANT .. ',bold'

-- Julia
lexers.STYLE_CHARACTER = lexers.STYLE_CONSTANT

-- Mediawiki
lexers.STYLE_BEHAVIOR_SWITCH = lexers.STYLE_KEYWORD

-- Moonscript
lexers.STYLE_TBL_KEY      = lexers.STYLE_REGEX
lexers.STYLE_SELF_REF     = lexers.STYLE_LABEL
lexers.STYLE_PROPER_IDENT = lexers.STYLE_CLASS
lexers.STYLE_FNDEF        = lexers.STYLE_PREPROCESSOR

-- reST
lexers.STYLE_LITERAL_BLOCK     = lexers.STYLE_EMBEDDED
lexers.STYLE_FOOTNOTE_BLOCK    = lexers.STYLE_LABEL
lexers.STYLE_CITATION_BLOCK    = lexers.STYLE_LABEL
lexers.STYLE_LINK_BLOCK        = lexers.STYLE_LABEL
lexers.STYLE_CODE_BLOCK        = lexers.STYLE_CODE
lexers.STYLE_DIRECTIVE         = lexers.STYLE_KEYWORD
lexers.STYLE_SPHINX_DIRECTIVE  = lexers.STYLE_KEYWORD
lexers.STYLE_UNKNOWN_DIRECTIVE = lexers.STYLE_KEYWORD
lexers.STYLE_SUBSTITUTION      = lexers.STYLE_VARIABLE
lexers.STYLE_INLINE_LITERAL    = lexers.STYLE_EMBEDDED
lexers.STYLE_ROLE              = lexers.STYLE_CLASS
lexers.STYLE_INTERPRETED       = lexers.STYLE_STRING

-- txt2tags
lexers.STYLE_LINE = 'bold'
for i = 1, 5 do lexers['STYLE_H' .. i] = lexers.STYLE_HEADING end
lexers.STYLE_IMAGE               = fg(c.green)
lexers.STYLE_STRIKE              = 'italics'
lexers.STYLE_TAGGED              = lexers.STYLE_EMBEDDED
lexers.STYLE_TAGGED_AREA         = lexers.STYLE_EMBEDDED
lexers.STYLE_TABLE_SEP           = fg(c.green)
lexers.STYLE_HEADER_CELL_CONTENT = fg(c.green)
