# Interactive Switch Health Console

This local dashboard connects to one Cisco IOS or Huawei VRP switch at a time. Enter the target IP on the connection screen, choose automatic detection or a vendor, and the console displays only the switch hostname and vendor. It never returns the target address, switch credentials, or raw command output to the browser.

## Start it

1. Confirm the shared `USERNAME`, `PASSWORD`, and `ENABLE_SECRET` at the top of `SwitchhealthStatuscheck.py` work on the Cisco and Huawei switches.
2. Run `python switch_health_dashboard.py` from this folder.
3. Open `http://127.0.0.1:8787`.
4. Enter a switch IP address and connect.

Use **Change switch** to clear the current connection before selecting another device.

## Data collected

| Component | Cisco IOS | Huawei VRP |
| --- | --- | --- |
| Processor | `show processes cpu` | `display cpu-usage` |
| Memory | `show processes memory` | `display memory-usage` |
| Cooling fans | `show environment all` | `display fan` |
| Power supply | `show environment all` | `display power` |
| Thermal sensors | `show environment all` | `display temperature` |

The selected component in the 3D chassis shows its parsed health state. The dashboard deliberately withholds the raw CLI responses so no sensitive device information appears in the interface.

## Thresholds

| Reading | Nominal | Review | Action needed |
| --- | --- | --- | --- |
| CPU | under 70% | 70–89% | 90%+ |
| Memory | under 75% | 75–89% | 90%+ |
| Hardware components | no flagged status | warning / marginal | fault / failure / critical |
