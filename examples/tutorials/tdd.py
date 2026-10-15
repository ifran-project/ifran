import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def generate_tdd_pattern(tdd):
    """
    Generate a compact TDD pattern.

    Example:
        5 DL slots + special slot + 4 UL slots
        -> DDDDDSUUUU
    """
    dl_slots = tdd.nrofDownlinkSlots
    ul_slots = tdd.nrofUplinkSlots

    pattern = (
        "D" * dl_slots
        + "S"
        + "U" * ul_slots
    )

    return pattern


def generate_symbol_pattern(tdd):
    """
    Generate a symbol-level representation.

    Each normal slot contains 14 OFDM symbols.
    The special slot contains:
        nrofDownlinkSymbols DL symbols
        remaining symbols as guard symbols
        nrofUplinkSymbols UL symbols

    Returns a string such as:
        DDDDDDDDDDDDDDD
        ...
    """
    dl_slots = tdd.nrofDownlinkSlots
    ul_slots = tdd.nrofUplinkSlots
    dl_symbols = tdd.nrofDownlinkSymbols
    ul_symbols = tdd.nrofUplinkSymbols

    # NR slot = 14 OFDM symbols for normal CP
    symbols_per_slot = 14

    # Normal DL and UL slots
    pattern = (
        "D" * (dl_slots * symbols_per_slot)
        + "D" * dl_symbols
        + "G" * (symbols_per_slot - dl_symbols - ul_symbols)
        + "U" * ul_symbols
        + "U" * (ul_slots * symbols_per_slot)
    )

    return pattern


def plot_tdd_pattern(tdd, gnb: str, savefile=None):
    """
    Generate a graphical representation of the TDD pattern.
    """

    dl_slots = tdd.nrofDownlinkSlots
    ul_slots = tdd.nrofUplinkSlots
    dl_symbols = tdd.nrofDownlinkSymbols
    ul_symbols = tdd.nrofUplinkSymbols

    symbols_per_slot = 14
    total_slots = dl_slots + 1 + ul_slots

    fig, ax = plt.subplots(figsize=(12, 2.5))

    colors = {
        "D": "#4C78A8",  # blue
        "G": "#F2CF5B",  # yellow
        "U": "#59A14F",  # green
    }

    # Plot normal DL slots
    for slot in range(dl_slots):
        x = slot
        ax.add_patch(
            Rectangle(
                (x, 0),
                1,
                1,
                facecolor=colors["D"],
                edgecolor="black",
            )
        )
        ax.text(
            x + 0.5,
            0.5,
            "D",
            ha="center",
            va="center",
            fontsize=14,
            color="white",
            fontweight="bold",
        )

    # Plot special slot
    special_slot = dl_slots

    # DL symbols
    dl_width = dl_symbols / symbols_per_slot
    ax.add_patch(
        Rectangle(
            (special_slot, 0),
            dl_width,
            1,
            facecolor=colors["D"],
            edgecolor="black",
        )
    )

    # Guard symbols
    guard_symbols = symbols_per_slot - dl_symbols - ul_symbols
    guard_width = guard_symbols / symbols_per_slot

    ax.add_patch(
        Rectangle(
            (special_slot + dl_width, 0),
            guard_width,
            1,
            facecolor=colors["G"],
            edgecolor="black",
        )
    )

    # UL symbols
    ul_width = ul_symbols / symbols_per_slot

    ax.add_patch(
        Rectangle(
            (special_slot + dl_width + guard_width, 0),
            ul_width,
            1,
            facecolor=colors["U"],
            edgecolor="black",
        )
    )

    ax.text(
        special_slot + 0.5,
        0.5,
        "S",
        ha="center",
        va="center",
        fontsize=14,
        color="black",
        fontweight="bold",
    )

    # Plot normal UL slots
    for i in range(ul_slots):
        x = dl_slots + 1 + i

        ax.add_patch(
            Rectangle(
                (x, 0),
                1,
                1,
                facecolor=colors["U"],
                edgecolor="black",
            )
        )

        ax.text(
            x + 0.5,
            0.5,
            "U",
            ha="center",
            va="center",
            fontsize=14,
            color="white",
            fontweight="bold",
        )

    # Axis formatting
    ax.set_xlim(0, total_slots)
    ax.set_ylim(0, 1)
    ax.set_yticks([])

    ax.set_xticks([i + 0.5 for i in range(total_slots)])
    ax.set_xticklabels(
        ["DL"] * dl_slots + ["SPECIAL"] + ["UL"] * ul_slots
    )

    ax.set_xlabel("Slot")
    ax.set_title(
        f"TDD Pattern for {gnb} — periodicity = "
        f"{tdd.periodicityMilliseconds}"
    )

    # Legend
    legend_elements = [
        Rectangle((0, 0), 1, 1, facecolor=colors["D"], label="Downlink"),
        Rectangle((0, 0), 1, 1, facecolor=colors["G"], label="Guard"),
        Rectangle((0, 0), 1, 1, facecolor=colors["U"], label="Uplink"),
    ]

    ax.legend(
        handles=legend_elements,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.25),
        ncol=3,
    )

    plt.tight_layout()
    if savefile is not None:
        plt.savefig(savefile, dpi=200, bbox_inches="tight")
    plt.show()
