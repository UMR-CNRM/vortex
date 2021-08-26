# Vortex's Promethee extension
You may find new custom Vortex Resources for running Promethee on HPC :

| Name | Type | Attributes | Description |
| ------ | ------ | ------ | ------ |
| `PrometheeAlgo` | Scriptbased algo component | **`kind`**,  `cmdline` | Algo component for executing Python 3.7 scripts with args |
| `PrometheeConfig` | Configfile resource | **`kind`**, **`scope`**, **`version`**, **`date`** | Specific JSON config file for Promethee |
| `PrometheeOutput` | Configfile resource | **`kind`**, **`promid`**, **`version`**, **`date`** | JSON output file identified by a promethee id, a version and a date |
| `PrometheeScript` | Executable resource | **`kind`**, **`language`** | Script launchable with args through a command line |
| `PrometheeGridPoint` | Gridfile | **`kind`**, **`model`**, **`geometry`**, **`date`**, **`param`**,**`begintime`**, **`endtime`**, **`cutoff`**, **`origin`**, **`nativefmt`** | Gridpoint resource with a single parameter and multiple terms |
| `PrometheeMask` | Gridfile resource | **`kind`**, **`promid`**, **`version`** | Geographical mask identified by a promethee id and a version |
