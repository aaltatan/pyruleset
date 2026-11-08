import re
from pathlib import Path

README = Path(__file__).parent.parent / "README.md"
BLOCK = re.compile(r"^```python\n(.*?)^```", re.DOTALL | re.MULTILINE)


class TestReadme:
    def test_code_blocks_run_in_order(self):
        # The first block is a teaser that uses names defined by the later ones.
        # shortcut: checks that the blocks run, not their "# result" comments; compare reprs if those drift.
        blocks = BLOCK.findall(README.read_text(encoding="utf-8"))[1:]
        namespace = {"__name__": "__main__"}

        for block in blocks:
            exec(block, namespace)  # noqa: S102

        assert len(blocks) >= 10
