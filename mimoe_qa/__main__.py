"""Enable `python -m mimoe_qa` without installing the package."""

from .cli import main

raise SystemExit(main())
