
from solcore import material, si

from solcore.absorption_calculator import search_db, download_db
from solcore.absorption_calculator.nk_db import search_db, create_nk_txt
import os
from solcore.structure import Layer, Junction
from solcore.solar_cell_solver import solar_cell_solver, default_options
from solcore.solar_cell import SolarCell
from solcore.light_source import LightSource
from solcore.constants import q
import numpy as np
import matplotlib.pyplot as plt
# download_db(confirm=True)


MgF2_pageid = search_db(os.path.join("MgF2", "Rodriguez-de Marcos"))[0][0];
ZnS_pageid = search_db(os.path.join("ZnS", "Querry"))[0][0];
MgF2 = material(str(MgF2_pageid), nk_db=True)();
ZnS = material(str(ZnS_pageid), nk_db=True)();

window = material("AlInP")(Al=0.52)
GaInP = material("GaInP")
BSF = material("AlGaAs")(Al=0.5)
epoxy = material("BK7")()

SiOx = material("SiO")()
SiN_191_pageid = search_db("Vogt-1.91")[0][0];
SiN_213_pageid = search_db("Vogt-2.13")[0][0];
SiN_191 = material(str(SiN_191_pageid), nk_db=True)();
SiN_213 = material(str(SiN_213_pageid), nk_db=True)();

Si = material("Si")

Al2O3 = material("Al2O3P")()
Al = material("Al")()

ARC_window = [
    Layer(97e-9, MgF2),
    Layer(41e-9, ZnS),
    Layer(17e-9, window, role="window"),
]

GaInP_junction = Junction([
    Layer(200e-9, GaInP( In=0.5, Nd=si("2e18cm-3"), hole_diffusion_length=si("300nm")), role="emitter"),
    Layer(750e-9, GaInP(In=0.5, Na=si("1e17cm-3"), electron_diffusion_length=si("800nm")), role="base"),
    Layer(500e-9, BSF, role="bsf")], kind="DA", sn=1, sp=1
)

spacer = [
    Layer(82e-9, ZnS),
    Layer(10e-6, epoxy), # real thickness is much higher, but since this layer is
    # non-absorbing at the relevant wavelength (> 650 nm) and treated incoherently,
    # this does not matter
]

spacer_noARC = [
    Layer(10e-6, epoxy),
]

Si_front_surf = [
    Layer(100e-9, SiOx),
    Layer(70e-9, SiN_191),
    Layer(15e-9, SiN_213),
    ]

Si_junction = Junction([
    Layer(1e-6, Si(Nd=si("2e18cm-3"), hole_diffusion_length=2e-6), role="emitter"),
    Layer(150e-6, Si(Na=si("2e15cm-3"), electron_diffusion_length=150e-6), role="base"),
], kind="DA", sn=0.1, sp=0.1)

Si_back_surf = [
    Layer(15e-9, Al2O3),
    Layer(120e-9, SiN_191)
]

n_coh_layers = len(ARC_window + GaInP_junction)
n_inc_layers = 1 + len(Si_front_surf + Si_junction + Si_back_surf)

wl = np.linspace(300, 1200, 600) * 1e-9

options = default_options
options.recalculate_absorption = True
options.wavelength = wl
options.optics_method = 'TMM'

AM15G = LightSource(source_type="standard", version="AM1.5g", x=wl*1e9,
                    output_units="photon_flux_per_nm")
                    
cell_no_ARC = SolarCell(
    ARC_window + GaInP_junction + spacer_noARC + Si_front_surf + Si_junction +
    Si_back_surf,
    substrate=Al,
)

cell_with_ARC = SolarCell(
    ARC_window + GaInP_junction + spacer + Si_front_surf + Si_junction + Si_back_surf,
    substrate=Al,
)


options.coherency_list = ['c']*(n_coh_layers) + ['i']*n_inc_layers
solar_cell_solver(cell_no_ARC, "optics", options)

GaInP_A = cell_no_ARC[3].layer_absorption + cell_no_ARC[4].layer_absorption
Si_A = cell_no_ARC[10].layer_absorption + cell_no_ARC[11].layer_absorption

options.coherency_list = ["c"]*(n_coh_layers + 1) + ['i']*n_inc_layers
solar_cell_solver(cell_with_ARC, "optics", options)

GaInP_A_ARC = cell_with_ARC[3].layer_absorption + cell_with_ARC[4].layer_absorption
Si_A_ARC = cell_with_ARC[11].layer_absorption + cell_with_ARC[12].layer_absorption

plt.figure()

plt.plot(wl * 1e9, GaInP_A_ARC, "-k", label="GaInP")
plt.plot(wl * 1e9, Si_A_ARC, "-r", label="Si")
plt.plot(wl * 1e9, cell_with_ARC.reflected, '-b', label="R")

plt.plot(wl * 1e9, GaInP_A, "--k", label="No middle ARC")
plt.plot(wl * 1e9, Si_A, "--r")
plt.plot(wl * 1e9, cell_no_ARC.reflected, '--b')

plt.legend(loc='upper right')
plt.xlabel("Wavelength (nm)")
plt.ylabel("Absorptance/Reflectance")
plt.tight_layout()
plt.show()

J_GaInP = q*np.trapz(GaInP_A * AM15G.spectrum()[1], wl*1e9)
J_Si = q*np.trapz(Si_A * AM15G.spectrum()[1], wl*1e9)

print("Limiting short-circuit currents without ARC (mA/cm2): {:.1f} / {:.1f}".format(
      J_GaInP/10, J_Si/10))

J_GaInP_ARC = q*np.trapz(GaInP_A_ARC * AM15G.spectrum()[1], wl*1e9)
J_Si_ARC = q*np.trapz(Si_A_ARC * AM15G.spectrum()[1], wl*1e9)

print("Limiting short-circuit currents with ARC (mA/cm2): {:.1f} / {:.1f}".format(
    J_GaInP_ARC/10, J_Si_ARC/10))
    
options.mpp = True
options.light_iv = True
options.voltages = np.linspace(-1.9, 0.1, 100)
options.light_source = AM15G

solar_cell = SolarCell(
    ARC_window + [GaInP_junction] + spacer + Si_front_surf + [Si_junction] +
    Si_back_surf,
    substrate=Al,
)
solar_cell_solver(solar_cell, 'qe', options)

plt.figure()
plt.plot(wl * 1e9, GaInP_A_ARC, "--k", label="GaInP only absorption")
plt.plot(wl * 1e9, Si_A_ARC, "--r", label="Si only absorption")
plt.plot(wl*1e9, solar_cell(0).eqe(wl), '-k')
plt.plot(wl*1e9, solar_cell(1).eqe(wl), '-r')
plt.legend(loc='upper right')
plt.xlabel("Wavelength (nm)")
plt.ylabel("Absorptance/EQE")
plt.ylim(0,1)
plt.tight_layout()
plt.show()

solar_cell_solver(solar_cell, 'iv', options)

plt.figure()
plt.plot(-options.voltages, -solar_cell.iv['IV'][1]/10, 'k', linewidth=3,
         label='Total (2-terminal)')
plt.plot(-options.voltages, solar_cell(0).iv(options.voltages)/10, 'b',
         label='GaInP')
plt.plot(-options.voltages, solar_cell(1).iv(options.voltages)/10, 'g',
         label='Si')
plt.text(0.1, 18, r"2-terminal $\eta$ = {:.2f}%".format(solar_cell.iv["Eta"]*100))
plt.legend()
plt.ylim(0, 20)
plt.xlim(0, 1.9)
plt.ylabel('Current (mA/cm$^2$)')
plt.xlabel('Voltage (V)')
plt.tight_layout()
plt.show()
    
