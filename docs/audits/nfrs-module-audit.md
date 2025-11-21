# NFRS Module Audit Report

**Date**: 2025-11-21
**Module Target**: `src/taskpy/modern/nfrs/`
**Auditor**: China the Summary Chicken
**Audit Type**: Legacy Dependency Analysis & Migration Assessment

---

## Executive Summary

The `modern/nfrs/` module is a **partially-implemented feature** that provides CLI interface and command handling for Non-Functional Requirements (NFRs) management. Currently, it has **2 direct legacy imports** from `taskpy.legacy` that couple the modern module to the old codebase. The module structure is clean, but **models.py is empty** and requires migration work. All NFR data handling currently delegates to legacy storage layer.

**Key Finding**: This module is **"almost finished" but incomplete** – CLI structure is in place, but modern equivalents need to be built.

---

## Legacy Imports Found

### Direct Imports in nfrs/commands.py

| Import | Source | Purpose | Status |
|--------|--------|---------|--------|
| `TaskStorage` | `taskpy.legacy.storage` | Load NFRs from `nfrs.toml` | **CRITICAL** |
| `print_error` | `taskpy.legacy.output` | Error message display | **MEDIUM** |

### Detailed Import Analysis

#### 1. `from taskpy.legacy.storage import TaskStorage`
- **Line**: 5 in `/src/taskpy/modern/nfrs/commands.py`
- **Usage Context**: Instantiated in `cmd_nfrs()` function
- **What it does**:
  - Initializes storage with project root path
  - Checks if TaskPy is initialized (via `is_initialized()`)
  - Loads NFR definitions from TOML configuration (`load_nfrs()`)
  - Returns dictionary of NFR objects mapped by ID

#### 2. `from taskpy.legacy.output import print_error`
- **Line**: 6 in `/src/taskpy/modern/nfrs/commands.py`
- **Usage Context**: Error handling in `cmd_nfrs()`
- **What it does**:
  - Displays error messages with optional title
  - Uses `boxy` terminal UI library for pretty output
  - Falls back to plain text if boxy unavailable

---

## What Each Import Does (Detailed Analysis)

### TaskStorage Class Analysis

**Location**: `src/taskpy/legacy/storage.py` lines 122-937

The TaskStorage class is a comprehensive persistence layer with many responsibilities:

| Responsibility | Implementation | Relevant to NFRS |
|---|---|---|
| Project initialization | `initialize()` method | Creates default `nfrs.toml` |
| NFR loading | `load_nfrs()` method | **DIRECTLY USED** in nfrs module |
| Task persistence | `read_task_file()`, `write_task_file()` | No |
| Manifest management | `_update_manifest_row()` | No |
| Epic loading | `load_epics()` | No |
| Milestone loading | `load_milestones()` | No |

**Specific to NFRs**: The `load_nfrs()` method (lines 523-547):

```python
def load_nfrs(self) -> Dict[str, NFR]:
    """Load NFR definitions from nfrs.toml."""
    # Reads TOML file from info_dir/nfrs.toml
    # Parses each NFR section into NFR dataclass
    # Returns dict mapping NFR-ID -> NFR object
```

**NFR Model Used**: `taskpy.legacy.models.NFR` dataclass (lines 325-345)

```python
@dataclass
class NFR:
    id: str                          # NFR-SEC-001
    category: str                    # SEC, PERF, TEST, etc.
    number: int                      # 001, 002, etc.
    title: str                       # Human-readable title
    description: str                 # Detailed description
    verification: Optional[str]      # How to verify compliance
    default: bool                    # Is default NFR?
```

### print_error Function Analysis

**Location**: `src/taskpy/legacy/output.py` lines 327-329

```python
def print_error(message: str, title: Optional[str] = None):
    """Print error message."""
    boxy_display(message, Theme.ERROR, title or "✗ Error")
```

**Dependency Chain**:
- `print_error()` → `boxy_display()` → subprocess call to `boxy` CLI
- Fallback: Plain text output if boxy unavailable
- Part of larger output system that supports: boxy, rolo (tables), plain text

---

## Migration Required: What Needs to Move/Copy

### Priority 1: CRITICAL - Core Models

**Task**: Migrate/copy NFR model to modern namespace

```
TARGET: src/taskpy/modern/nfrs/models.py
SOURCE: src/taskpy/legacy/models.py (lines 325-345)
ACTION: Copy NFR dataclass + to_dict() method

CHANGES NEEDED:
- Remove dependency on legacy.models import
- Ensure imports are from modern namespace
- Update any references in commands.py
```

### Priority 2: CRITICAL - Storage Abstraction

**Task**: Create modern storage adapter or migrate TaskStorage

**Option A - Modern Storage (Preferred)**:
```
TARGET: src/taskpy/modern/nfrs/storage.py (NEW)
RESPONSIBILITY:
  - load_nfrs() method only
  - Isolated from other storage concerns
  - TOML parsing and NFR object creation
```

**Option B - Storage Adapter**:
```
TARGET: src/taskpy/modern/nfrs/storage.py (NEW)
RESPONSIBILITY:
  - Wrap legacy.storage.TaskStorage
  - Abstract only NFR-relevant methods
  - Eventually replace legacy dependency
```

**Recommendation**: **Option A** - Extract just `load_nfrs()` logic into modern module, eliminate TaskStorage dependency entirely.

### Priority 3: MEDIUM - Output/Display

**Task**: Replace `print_error()` with modern output module

**Current State**:
- Legacy `output.py` has boxy/rolo integration (good)
- Modern equivalent doesn't exist yet

**Recommended Action**:
- Create `src/taskpy/modern/output.py` or reuse legacy (temporary)
- Could be extracted as shared library between modern & legacy
- For now: keep legacy output dependency (low-risk)

### Priority 4: MEDIUM - Empty models.py

**Current State**:
```python
# src/taskpy/modern/nfrs/models.py
"""Data models for NFRs feature."""

# Will contain NFR-specific models when migrated from legacy
```

**Required**:
- Import or define NFR, VerificationStatus, and related enums
- Add any modern-specific model extensions
- Document model versioning/compatibility

---

## Potential Issues/Bugs Found

### 🚨 CRITICAL Issues

#### 1. **Incomplete Migration Pattern**

**Issue**: Models are stubbed but not implemented
**Impact**: Code appears complete but models.py is empty
**Risk**: Type hints in commands.py fail if models aren't properly imported
**Evidence**:
```python
# commands.py uses NFR objects without importing them
nfrs = storage.load_nfrs()  # Returns Dict[str, NFR]
for nfr_id, nfr in sorted(nfrs.items()):
    # nfr.default, nfr.title, nfr.description, nfr.verification accessed
```

**Fix**: Import NFR model in commands.py:
```python
from taskpy.legacy.models import NFR  # Temporary
# Or: from .models import NFR  # Once migrated
```

#### 2. **No Type Hints on cmd_nfrs()**

**Issue**: Function lacks return type annotation
**Code**:
```python
def cmd_nfrs(args):  # args has no type hint
    """List NFRs."""
```

**Risk**: IDE autocomplete fails, static type checkers won't validate
**Fix**:
```python
from argparse import Namespace
from typing import Optional

def cmd_nfrs(args: Namespace) -> Optional[int]:
    """List NFRs."""
```

---

### ⚠️ MAJOR Issues

#### 3. **No Error Handling for TOML Parsing Failures**

**Issue**: If `nfrs.toml` is corrupted, code will crash
**Location**: `TaskStorage.load_nfrs()` at line 532-547
**Code**:
```python
with open(nfrs_file, 'rb') as f:
    data = tomllib.load(f)  # Can raise tomllib.TOMLDecodeError
```

**Impact**: No user-friendly error message
**Fix Needed**: Wrap with try/except in commands.py:
```python
try:
    nfrs = storage.load_nfrs()
except Exception as e:
    print_error(f"Failed to load NFRs: {e}")
    sys.exit(1)
```

#### 4. **Unhandled Empty Results**

**Issue**: If no NFRs loaded, output is confusing
**Code**:
```python
nfrs = storage.load_nfrs()
# ... nfrs could be empty dict {}

if args.defaults:
    nfrs = {nfr_id: nfr for nfr_id, nfr in nfrs.items() if nfr.default}
    # Silent if no defaults exist

for nfr_id, nfr in sorted(nfrs.items()):
    # Prints nothing if nfrs is empty
```

**Issue**: No feedback to user if no NFRs found
**Fix**: Add informational output
```python
if not nfrs:
    print_info("No NFRs configured")
    return 0
```

#### 5. **File Not Found Scenario Unhandled**

**Issue**: If `nfrs.toml` doesn't exist, returns empty dict silently
**Location**: `storage.py` lines 528-530
**Code**:
```python
nfrs_file = self.info_dir / "nfrs.toml"
if not nfrs_file.exists():
    return {}  # Silent failure
```

**Problem**: User won't know they need to run `taskpy init` with explicit NFR setup
**Current Workaround**: `is_initialized()` check catches this indirectly

---

### 🟡 MINOR Issues

#### 6. **Missing Verification Field Output**

**Issue**: Incomplete output formatting
**Code**:
```python
if nfr.verification:
    print(f"  Verification: {nfr.verification}")
```

**Problem**: Prints raw TOML string, not user-friendly
**Example Output**:
```
NFR-SEC-001 [DEFAULT]: Code must be free of common security vulnerabilities
  Code must be free of common security vulnerabilities
  Verification: Run security linters and manual code review
```

**Suggestion**: Could use formatting/wrapping for better readability

#### 7. **No Support for Custom NFR Categories**

**Issue**: Commands.py hardcoded to display all NFRs
**Missing Features**:
- Filter by category (--category SEC)
- Filter by default status (--defaults only, no --custom)
- Search by keyword (--search "performance")
- Sort options (--sort name|category|number)

**Current Limitation**:
```python
parser.add_argument(
    '--defaults',
    action='store_true',
    help='Show only default NFRs'
)
# No other filtering options
```

---

### 📋 Code Smells & Maintenance Concerns

#### 8. **Inconsistent Module Structure**

**Issue**: Similar to legacy.commands.py pattern, but modern is incomplete

| File | Purpose | Status |
|------|---------|--------|
| `cli.py` | CLI registration | ✓ Complete |
| `commands.py` | Command logic | ⚠️ Partial (import issues) |
| `models.py` | Data models | ❌ Empty |
| `storage.py` | Persistence | ❌ Missing |

**Recommendation**: Complete pattern before marking "modern"

#### 9. **Tight Coupling to Legacy Storage**

**Issue**: Commands.py directly instantiates TaskStorage
**Problem**: Can't test or mock storage behavior independently

**Better Pattern**:
```python
# Dependency injection
def cmd_nfrs(args, nfr_storage: Optional[NFRStorage] = None):
    if nfr_storage is None:
        nfr_storage = ModernNFRStorage(Path.cwd())

    nfrs = nfr_storage.load_nfrs()
```

---

## Dependencies Analysis

### Dependency Graph

```
src/taskpy/modern/nfrs/
├── commands.py
│   ├── taskpy.legacy.storage.TaskStorage       [EXTERNAL DEPENDENCY]
│   │   └── taskpy.legacy.models.NFR            [MODEL DEPENDENCY]
│   │       └── taskpy.legacy.models (enums)    [TRANSITIVE]
│   ├── taskpy.legacy.output.print_error        [EXTERNAL DEPENDENCY]
│   │   └── taskpy.legacy.output (full module)  [TRANSITIVE]
│   └── sys, pathlib (stdlib)                   [OK]
├── cli.py
│   ├── .commands.cmd_nfrs                      [LOCAL]
│   ├── argparse (stdlib)                       [OK]
│   └── No external deps
├── models.py
│   └── (EMPTY - NO DEPENDENCIES)
└── __init__.py
    └── Imports cli, models, commands           [LOCAL]
```

### Dependency Summary Table

| Dependency | Module | Scope | Risk | Notes |
|---|---|---|---|---|
| `taskpy.legacy.storage` | commands.py | Direct | CRITICAL | Must migrate or replace |
| `taskpy.legacy.output` | commands.py | Direct | MEDIUM | Could share with other modules |
| `taskpy.legacy.models` | storage (transitive) | Transitive | CRITICAL | Model migration required |
| `argparse` | cli.py | Direct | LOW | Standard library |
| `sys, pathlib` | commands.py | Direct | LOW | Standard library |

### What This Module Depends ON (imports from)

**External Dependencies** (outside modern.nfrs):
1. **taskpy.legacy.storage.TaskStorage** - Full persistence layer
   - Only uses: `is_initialized()`, `load_nfrs()`, `root` path

2. **taskpy.legacy.output.print_error** - Error display function
   - Only uses: single function call with message + optional title

3. **taskpy.legacy.models.NFR** - Data class (implicit via storage)
   - Only uses: NFR.default, NFR.title, NFR.description, NFR.verification

**Internal Dependencies** (within modern.nfrs):
1. **cli.py** → **commands.py** (cmd_nfrs function)
2. **__init__.py** → **cli, models, commands** modules

**No Dependencies On**:
- Modern CLI framework (used by parent)
- Modern task model
- Modern storage other than NFR loading
- Tour or other modern modules

---

## Verification Tests Performed

### ✓ File Existence Checks
- [x] All 4 expected files exist (cli.py, commands.py, models.py, __init__.py)
- [x] No orphaned .pyc or cache files

### ✓ Import Statement Analysis
- [x] Scanned all Python files for `taskpy.legacy` imports
- [x] Found exactly 2 legacy imports (as documented)
- [x] Verified no circular imports between modules

### ✓ Code Structure Validation
- [x] CLI registration pattern matches expected format
- [x] Command function signature compatible with TaskPy CLI framework
- [x] TOML config path correctly references `data/kanban/info/nfrs.toml`

### ✓ Dependency Chain Verification
- [x] TaskStorage.load_nfrs() returns Dict[str, NFR]
- [x] NFR model has required fields (id, category, number, title, description, verification, default)
- [x] print_error() function signature verified

### ⚠️ Incomplete Verifications
- [ ] Runtime testing (requires initialized TaskPy project)
- [ ] TOML parsing edge cases
- [ ] Large NFR dataset performance
- [ ] Integration with CLI framework

---

## Key Takeaways & Actionable Recommendations

### Immediate Actions (Before Production)

1. **Fix Type Hints**: Add return type to `cmd_nfrs()` and type hint for `args` parameter
   ```python
   def cmd_nfrs(args: argparse.Namespace) -> None:
   ```

2. **Import NFR Model**: commands.py must properly import NFR class
   ```python
   from taskpy.legacy.models import NFR  # Or modern equiv after migration
   ```

3. **Add Empty Result Handling**: Inform user if no NFRs configured
   ```python
   if not nfrs:
       print("ℹ No NFRs configured. Run: taskpy init")
       return 0
   ```

### Short-term (Next 1-2 Sprints)

4. **Implement models.py**: Migrate NFR dataclass to modern namespace
   ```python
   # src/taskpy/modern/nfrs/models.py
   from dataclasses import dataclass, field
   from typing import Optional

   @dataclass
   class NFR:
       # Copy from legacy.models...
   ```

5. **Extract NFRStorage**: Create modern-only persistence layer
   - Extract `load_nfrs()` logic from TaskStorage
   - Make it testable and mockable
   - Located: `src/taskpy/modern/nfrs/storage.py`

6. **Add Error Handling**: Wrap TOML parsing with try/except
   ```python
   try:
       nfrs = storage.load_nfrs()
   except Exception as e:
       print_error(f"NFR configuration error: {e}")
       return 1
   ```

### Medium-term (Sprint 2-3)

7. **Add Filtering Options**: Extend CLI capabilities
   - `--category SEC` filter by category
   - `--search text` search by title/description
   - `--sort` options for different orderings

8. **Create Shared Output Module**: Extract output functions
   - Modern and legacy share formatting
   - Consolidate boxy/rolo integration
   - One source of truth for styling

9. **Implement Tests**: Unit tests for commands and models
   - Mock storage layer
   - Test formatting with various NFR datasets
   - Verify error cases

### Long-term (Maintenance)

10. **Complete Deprecation**: Remove legacy imports entirely
    - Makes modern truly independent
    - Enables easier refactoring
    - Improves test isolation

---

## Questions & Answers

### Q: Is the nfrs module ready for use?
**A**: Technically functional, but **not production-ready**. The module can list NFRs, but has missing type hints, minimal error handling, and empty models.py. Recommended to complete Priority 1 & 2 migrations before release.

### Q: How long would migration take?
**A**: Estimated 2-4 hours for developer familiar with codebase:
- Migrate NFR model: 30 min
- Create modern storage: 60-90 min
- Fix type hints & errors: 30 min
- Testing: 60 min

### Q: Can I use legacy storage temporarily?
**A**: Yes, but plan replacement. Current setup is functional for MVP, but creates technical debt. The legacy storage is tightly coupled to Task management, making it harder to scale NFR features independently.

### Q: What's blocking new NFR features?
**A**:
1. No filtering/search CLI options
2. No programmatic API (only CLI)
3. No relationship linking between NFRs and tasks
4. No validation of NFR references in tasks

### Q: How do default NFRs work?
**A**: Defined in `data/kanban/info/nfrs.toml` with `default = true` field. The `--defaults` flag filters to show only those. No automatic application to new tasks in current implementation (though config supports `apply_default_nfrs` option in config.toml).

---

## Certification

**This audit confirms the following:**

✓ Module `src/taskpy/modern/nfrs/` exists with 4 files
✓ Exactly 2 legacy imports identified and documented
✓ All legacy dependencies are from `taskpy.legacy` namespace
✓ No circular imports or external package dependencies
✓ CLI registration pattern is valid and functional
✓ Commands follow TaskPy framework conventions

**Audit Limitations**: This analysis is based on static code review only. Runtime behavior, performance characteristics, and integration with full CLI system are NOT verified. Additional testing in initialized project environment recommended.

---

## Disclaimer

This audit represents the **status of files reviewed** at `/home/xnull/repos/code/python/snekfx/task-py/src/taskpy/modern/nfrs/` as of 2025-11-21.

**Important Notes**:
- This analysis does NOT represent the true operational state of the entire TaskPy system
- Only the nfrs module was examined; integration points with other modules assumed correct
- Recommendations are suggestions based on code patterns, not requirements
- Hidden files, compiled bytecode, or test files may contain additional information not reviewed
- Configuration in `nfrs.toml` was analyzed through storage.py code, not actual file inspection
- Migration difficulty estimates are rough and depend on existing test coverage

**For authoritative validation**, perform:
1. Runtime testing with actual TaskPy initialization
2. Review of test files (`tests/test_nfrs*.py`)
3. Integration testing with CLI framework
4. Performance testing with large NFR datasets
5. Code review with primary maintainer

---

## References

**Files Analyzed**:
- `/home/xnull/repos/code/python/snekfx/task-py/src/taskpy/modern/nfrs/__init__.py` (6 lines)
- `/home/xnull/repos/code/python/snekfx/task-py/src/taskpy/modern/nfrs/cli.py` (50 lines)
- `/home/xnull/repos/code/python/snekfx/task-py/src/taskpy/modern/nfrs/commands.py` (29 lines)
- `/home/xnull/repos/code/python/snekfx/task-py/src/taskpy/modern/nfrs/models.py` (4 lines)

**Legacy Files Cross-Referenced**:
- `/home/xnull/repos/code/python/snekfx/task-py/src/taskpy/legacy/storage.py` (937 lines)
- `/home/xnull/repos/code/python/snekfx/task-py/src/taskpy/legacy/output.py` (405 lines)
- `/home/xnull/repos/code/python/snekfx/task-py/src/taskpy/legacy/models.py` (410 lines)

**Total Lines Analyzed**: 1,841 lines of code

---

<div style="text-align: center; margin-top: 2em; padding: 1em; border-top: 2px solid #ddd;">

**🐔 Egg Laid By: China, The Summary Chicken**

*Master of Summarization • Champion of Code Audits • Keeper of Eggs*

```
    ^__^
    (oo)\_______
    (__)\       )\/\
        ||----w |
        ||     ||
```

**Cluck! 🐓 Your audit egg is ready for hatching!**

Reviewed with care, attention to detail, and a genuine desire to help you understand your codebase. May this summary help guide your migration efforts!

*Feed China when you're done reading! 🌾*

</div>
