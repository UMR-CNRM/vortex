with open("ICMSHFCSTINIT", "r") as f:
    analysis_ctent = f.readlines()

with open("fort.4", "r") as f:
    namel_ctent = f.readline()

term = int(namel_ctent.strip().split("=")[1])

for iterm in range(1, term + 1):
    with open(f"ICMSHFCST+{iterm:02d}:00.grib", "w") as f:
        f.write(f"Content of the file for term {iterm}\n")
