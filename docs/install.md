# Installation

pyruleset needs **Python 3.12 or newer**.

=== "uv"

    ```bash
    uv add pyruleset
    ```

=== "pip"

    ```bash
    pip install pyruleset
    ```

Its only dependency is [pyvocabulary](https://pypi.org/project/pyvocabulary/), a small
package by the same author that adds JSON paths to compiler errors.

The packages that usually supply conditions and values are optional. Install the ones you
use:

=== "uv"

    ```bash
    uv add pyspecification pyformula pyflowstep
    ```

=== "pip"

    ```bash
    pip install pyspecification pyformula pyflowstep
    ```

## Check it works

```python
from pyruleset import otherwise, when

sign = when(lambda n: n < 0, lambda _: "negative") | otherwise(lambda _: "non-negative")

assert sign(-3) == "negative"
assert sign(0) == "non-negative"
```
