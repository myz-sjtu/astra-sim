from matplotlib import pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import matplotlib as mpl
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams["font.family"] = "serif"
mpl.rcParams["font.serif"] = ["Times New Roman"]
mpl.rcParams["mathtext.fontset"] = "stix"

filename = 'large_pfc'

long_labels = ['dst_pfc_large','dst_pfc_dcqcn_large','dst_pfc_hpcc_large','dst_pfc_timely_large']
long_values = []
short_labels = ['src_pfc','src_pfc_dcqcn','src_pfc_hpcc','src_pfc_timely']
short_values = []

values = [short_values, long_values]

tab20_colors = plt.get_cmap('tab20').colors
colors = [tab20_colors[1], tab20_colors[7]]
font = FontProperties(weight='bold', size=22)
fig, ax = plt.subplots(figsize=(9, 5.5))

x_labels = ['PFC only', 'PFC+DCQCN', 'PFC+HPCC', 'PFC+Timely']
legends = ['Source Congestion','Remote Congestion']
x_pos = np.linspace(100, 200, len(x_labels))
bar_width = 10

custom_patches1 = []
for i in range(2):
    ax.bar(x_pos + i * bar_width, values[i], label='',
           color=colors[i], width=bar_width, edgecolor='black', lw=1)
    custom_patches1.append(Patch(facecolor=colors[i], label=legends[i]))

ax.set_ylabel("PFC Pause Duration (%)", fontproperties=font)

ax.set_yscale('log')
ax.set_ylim(0.003, 100)
ax.set_xlim(x_pos[0] - bar_width, x_pos[-1] + bar_width * 2)

ax.set_xticks(x_pos + bar_width/2)
ax.set_xticklabels(x_labels, fontproperties=FontProperties(weight='bold', size=16))
ax.grid(True, linestyle='--', alpha=0.7)
ax.tick_params(axis='both', labelsize=18)
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:g}%'))

plt.tight_layout()
# custom_patches1[1],custom_patches1[3] = custom_patches1[3], custom_patches1[1]
# custom_patches1[2],custom_patches1[3] = custom_patches1[3], custom_patches1[2]
ax.legend(handles=custom_patches1, prop=FontProperties(weight='bold', size=15), ncol=1,
          loc='upper right', bbox_to_anchor=(0.8, 0.98), framealpha=0.65)


plt.savefig(f"{filename}.pdf", bbox_inches='tight')
plt.show()
