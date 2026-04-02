
import re

TOOL_PATTERNS = {
    "cursor": (r"\bcursor\b",),
    "claude_code": (r"\bclaude code\b", r"\bclaude\b"),
    "codex": (r"\bopenai codex\b", r"\bcodex\b"),
    "copilot": (r"\bgithub copilot\b", r"\bcopilot\b"),
    "gemini": (r"\bgemini code assist\b", r"\bgemini\b"),
    "replit": (r"\breplit\b", r"\brepl\.it\b"),
    "aider": (r"\baider\b",),
    "windsurf": (r"\bwindsurf\b", r"\bcodeium\b"),
    "cline": (r"\bcline\b",),
    "opencode": (r"\bopencode\b",),
}

FACET_PATTERNS = {
    "reason": {
        "speed": (
            r"\bfast\b",
            r"\bfaster\b",
            r"\bspeed\b",
            r"\bquick\b",
            r"\bquickly\b",
            r"\blatency\b",
            r"\bproductivity\b",
        ),
        "code_quality": (
            r"\bcode quality\b",
            r"\bclean code\b",
            r"\bmaintainab",
            r"\breadab",
            r"\bbest practice",
            r"\bwell-structured\b",
        ),
        "correctness": (
            r"\bcorrect\b",
            r"\bcorrectness\b",
            r"\baccura",
            r"\bwrong\b",
            r"\bbroken\b",
            r"\bcompil",
            r"\bpasses\b",
            r"\bworks\b",
        ),
        "ux": (
            r"\beasy to use\b",
            r"\bease of use\b",
            r"\bfriction\b",
            r"\bergonomic",
            r"\bautocomplete\b",
            r"\binterface\b",
            r"\bui\b",
            r"\bux\b",
        ),
        "integrations": (
            r"\bintegration",
            r"\bplugin\b",
            r"\bextension\b",
            r"\bide\b",
            r"\bvscode\b",
            r"\bvs code\b",
            r"\bjetbrains\b",
            r"\bmarketplace\b",
        ),
    },
    "workflow": {
        "prototyping": (
            r"\bprototype",
            r"\bprototyping\b",
            r"\bmvp\b",
            r"\bscaffold",
            r"\bboilerplate\b",
            r"\bfirst draft\b",
            r"\bvibe cod",
        ),
        "debugging": (
            r"\bdebug",
            r"\bdebugging\b",
            r"\bbug\b",
            r"\berror\b",
            r"\bfix\b",
            r"\btrace\b",
            r"\brepro\b",
        ),
        "refactoring": (
            r"\brefactor",
            r"\brefactoring\b",
            r"\brewrite\b",
            r"\bcleanup\b",
            r"\brestructure\b",
            r"\btechnical debt\b",
        ),
        "testing": (
            r"\btest\b",
            r"\btesting\b",
            r"\bunit test",
            r"\bintegration test",
            r"\bpytest\b",
            r"\bcoverage\b",
            r"\bspec\b",
        ),
    },
    "trust": {
        "production": (
            r"\bproduction\b",
            r"\bprod\b",
            r"\bship\b",
            r"\benterprise\b",
            r"\bdeploy",
            r"\bin production\b",
        ),
        "reliability": (
            r"\breliable\b",
            r"\breliability\b",
            r"\bstable\b",
            r"\bstability\b",
            r"\bconsistent\b",
            r"\bdependable\b",
        ),
        "hallucination": (
            r"\bhallucinat",
            r"\bmakes things up\b",
            r"\bmade up\b",
            r"\blie[sd]?\b",
            r"\binvent",
            r"\brandom crap\b",
        ),
        "privacy": (
            r"\bprivacy\b",
            r"\bprivate\b",
            r"\bdata leak\b",
            r"\bself-host",
            r"\bon-prem\b",
            r"\blocal model\b",
            r"\boffline\b",
        ),
    },
}

VS_PATTERN = re.compile(r"\bvs\.?\b|\bversus\b", re.IGNORECASE)
BETTER_PATTERN = re.compile(r"\bbetter than\b|\bworse than\b|\bcompared to\b|\bprefer\b.*\bover\b", re.IGNORECASE)
SWITCH_PATTERN = re.compile(
    r"\bswitched from\b|\bmoved from\b|\bwent from\b|\btransitioned from\b|\bfrom\b.+?\bto\b",
    re.IGNORECASE,
)


def _compile_mapping(patterns):
    return {
        label: [re.compile(pattern, re.IGNORECASE) for pattern in label_patterns]
        for label, label_patterns in patterns.items()
    }


COMPILED_TOOLS = _compile_mapping(TOOL_PATTERNS)
COMPILED_FACETS = {name: _compile_mapping(mapping) for name, mapping in FACET_PATTERNS.items()}


def _match_labels(text, compiled_patterns):
    matches = []
    for label, patterns in compiled_patterns.items():
        if any(pattern.search(text) for pattern in patterns):
            matches.append(label)
    return matches


def extract_tools(text):
    positions = {}
    for tool_name, patterns in COMPILED_TOOLS.items():
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                positions[tool_name] = min(positions.get(tool_name, match.start()), match.start())
    return [tool for tool, _ in sorted(positions.items(), key=lambda item: item[1])]

#metadata for derived indices
def derive_metadata(text):
    tools = extract_tools(text)
    metadata = {
        "tool": tools,
        "reason": _match_labels(text, COMPILED_FACETS["reason"]),
        "workflow": _match_labels(text, COMPILED_FACETS["workflow"]),
        "trust": _match_labels(text, COMPILED_FACETS["trust"]),
        "comparison": [],
    }

    comparison_labels = []
    if VS_PATTERN.search(text):
        comparison_labels.append("vs")
        if len(tools) >= 2:
            comparison_labels.append(f"{tools[0]}_vs_{tools[1]}")
    if BETTER_PATTERN.search(text):
        comparison_labels.append("better_than")
    if SWITCH_PATTERN.search(text):
        comparison_labels.append("switch")
        if len(tools) >= 2:
            comparison_labels.append(f"{tools[0]}->{tools[1]}")

    metadata["comparison"] = comparison_labels
    return metadata
