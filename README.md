# robobrokerage
interacting with popular online broker platforms
1) login (no automation)
2) place simple trade
3) download recent transactions
3) download positions

# How to install locally
pip install <dev_repo_dir>

---

# Session notes (continue from here)

## What was done

A full restructure from `prev_ver/robobrokerage` into this directory.

**Removed:**
- `fid_page_position_v1.py` — v3 always wins, `verify_header_version` hardcoded to True
- `pricing_common.py` — was intended to replace `trade_common.py` but abandoned; no external call sites
- `legacy/` directory — forgotten leftover from an earlier cleanup
- Date-stamped filenames (e.g. `fid_page_activity_20250321.py`) — replaced with canonical names
- Dead/commented code, unused imports throughout

**Bugs fixed:**
- `trade_common.py`: `raise Error(...)` → `raise ValueError(...)` (`Error` was undefined)
- `fid_page_activity.py`: `cutoff_dt=today()` as default arg was evaluated at import time, not call time → fixed to `cutoff_dt=None` with `if cutoff_dt is None: cutoff_dt = today()` in body
- `fid_menu_accounts.py`: `partial_label.upper()` would crash on `None` → `ValueError` guard added; `subacct` is now a required keyword arg (no `=None` default) in `get_history`, `get_positions`, `show_order_manage_page`
- `fid_page_order.py`: `raise BaseException("timeout")` → `raise TimeoutError(...)`
- `fid_page_activity.py`: dead code after `return` in inner `process_order` function removed

**Design changes:**
- `present_broker_login_page()`: Fidelity now blocks automated login; method now only pre-fills username, fake password fill removed. User must enter password and complete 2FA manually.
- `select_stock()` dead function removed from `fid_page_order.py`
- `helper_download_formatter.py`: `sys.path.append` hack and `print(common_dir)` removed
- `populate_login_info()` method removed (was dead code)

## What still needs to be done

- **Testing**: the new code has not been tested against a live Fidelity session yet. All logic is carried faithfully from prev_ver but the refactoring should be verified.
- **Version-switching mechanism**: discussed but deferred. The current code uses one canonical version per page module. When Fidelity rolls UI changes, the plan is to add a version registry + optional `is_page_version_match(driver)` detection protocol per module. To be designed after this restructure is validated.

## File map (new → old)

| New file | Replaces |
|---|---|
| `fidelity_webbroker.py` | `fidelity_webbroker_20251118.py` |
| `fidelity/fid_menu_accounts.py` | `fidelity/fid_menu_accounts_20231207.py` |
| `fidelity/fid_page_auth.py` | `fidelity/fid_page_auth_20230916.py` |
| `fidelity/fid_page_summary.py` | `fidelity/fid_page_summary_20241115.py` |
| `fidelity/fid_page_position.py` | `fidelity/fid_page_position_v3.py` |
| `fidelity/fid_page_activity.py` | `fidelity/fid_page_activity_20250321.py` |
| `fidelity/fid_page_order.py` | `fidelity/fid_page_order_20241015.py` |
| `trade_common.py` | `trade_common.py` (same name, bug fixed) |
| *(removed)* | `pricing_common.py` |
| *(removed)* | `fidelity/fid_page_position_v1.py` |
| *(removed)* | `fidelity/legacy/` |
