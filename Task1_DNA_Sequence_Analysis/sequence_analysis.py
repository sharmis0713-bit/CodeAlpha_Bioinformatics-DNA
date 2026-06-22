from Bio import Entrez, SeqIO
from Bio.Blast import NCBIWWW, NCBIXML
from Bio import pairwise2
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
import time
import os

Entrez.email = "sharmis0713@gmail.com"
RESULTS_DIR = "results"
REPORT_DIR = "report"

def fetch_sequence(accession_id):
    print(f"Fetching sequence {accession_id} from NCBI...")
    handle = Entrez.efetch(
        db="nucleotide",
        id=accession_id,
        rettype="fasta",
        retmode="text"
    )
    record = SeqIO.read(handle, "fasta")
    handle.close()
    fasta_filename = f"{RESULTS_DIR}/insulin_sequence.fasta"
    SeqIO.write(record, fasta_filename, "fasta")
    print(f"Sequence saved! Length: {len(record.seq)} letters")
    print(f"Sequence ID: {record.id}")
    return record

def run_blast(record):
    print("\nSubmitting sequence to BLAST...")
    print("This will take 1-2 minutes. Please wait...")
    result_handle = NCBIWWW.qblast(
        program="blastn",
        database="nt",
        sequence=record.seq,
        hitlist_size=20
    )
    blast_xml = f"{RESULTS_DIR}/blast_results.xml"
    with open(blast_xml, "w") as out_handle:
        out_handle.write(result_handle.read())
    result_handle.close()
    print("BLAST search complete! Results saved.")
    return blast_xml

def parse_blast_results(blast_xml):
    print("\nParsing BLAST results...")
    results = []
    with open(blast_xml) as result_handle:
        blast_records = NCBIXML.parse(result_handle)
        blast_record = next(blast_records)
        for alignment in blast_record.alignments:
            for hsp in alignment.hsps:
                identity_percent = (hsp.identities / hsp.align_length) * 100
                title = alignment.title
                organism = title.split("|")[-1].strip()[:40]
                if "Homo sapiens" in title:
                    organism = "Homo sapiens - " + organism[:25]
                result = {
                    "organism": organism,
                    "identity": round(identity_percent, 2),
                    "evalue": hsp.expect,
                    "bit_score": hsp.bits,
                    "align_length": hsp.align_length,
                    "gaps": hsp.gaps
                }
                results.append(result)
                break
    print(f"\nTop {len(results)} BLAST matches found:")
    print("-" * 60)
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['organism']}")
        print(f"   Identity: {r['identity']}%  |  E-value: {r['evalue']}  |  Bit Score: {r['bit_score']}")
        print()
    return results

def create_visualization(results):
    print("\nCreating BLAST visualization...")

    organisms = [r["organism"][:35] for r in results]
    identities = [r["identity"] for r in results]
    evalues = [r["evalue"] for r in results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, max(6, len(results) * 0.5 + 2)))
    fig.suptitle("Human Insulin Gene — BLAST Analysis Results",
                 fontsize=15, fontweight="bold", y=1.01)

    # ── Chart 1: Identity % (horizontal bar) ──────────────────────
    colors = ["#27ae60" if i >= 90 else "#e67e22" if i >= 70 else "#c0392b"
              for i in identities]

    bars = ax1.barh(range(len(organisms)), identities, color=colors,
                    height=0.6, edgecolor="white", linewidth=0.5)

    ax1.set_yticks(range(len(organisms)))
    ax1.set_yticklabels(organisms, fontsize=8)
    ax1.set_xlabel("Identity (%)", fontsize=10)
    ax1.set_title("Sequence Identity Across Species", fontsize=11, fontweight="bold", pad=10)
    ax1.set_xlim(0, 108)
    ax1.axvline(x=90, color="#27ae60", linestyle="--", alpha=0.6, linewidth=1)
    ax1.axvline(x=70, color="#e67e22", linestyle="--", alpha=0.6, linewidth=1)
    ax1.invert_yaxis()
    ax1.spines[["top", "right"]].set_visible(False)

    for bar, val in zip(bars, identities):
        ax1.text(val + 0.8, bar.get_y() + bar.get_height() / 2,
                 f"{val}%", va="center", ha="left", fontsize=7.5, fontweight="bold")

    legend_elements = [
        Patch(facecolor="#27ae60", label="≥90% — Highly similar"),
        Patch(facecolor="#e67e22", label="70–89% — Moderate"),
        Patch(facecolor="#c0392b", label="<70% — Distantly related"),
    ]
    ax1.legend(handles=legend_elements, loc="lower right", fontsize=8, framealpha=0.8)

    # ── Chart 2: E-values (horizontal bar, log scale) ─────────────
    evalues_fixed = [max(e, 1e-200) for e in evalues]

    ax2.barh(range(len(organisms)), evalues_fixed,
             color="#2980b9", height=0.6, edgecolor="white", linewidth=0.5)

    ax2.set_yticks(range(len(organisms)))
    ax2.set_yticklabels(organisms, fontsize=8)
    ax2.set_xlabel("E-value (log scale — lower is better)", fontsize=10)
    ax2.set_title("E-values for Each BLAST Match", fontsize=11, fontweight="bold", pad=10)
    ax2.set_xscale("log")
    ax2.set_xlim(1e-200, 10)
    ax2.invert_yaxis()
    ax2.spines[["top", "right"]].set_visible(False)

    for i, (val, e) in enumerate(zip(range(len(organisms)), evalues_fixed)):
        label = f"{val:.0e}" if val > 0 else "0"
        ax2.text(evalues_fixed[i] * 2, i,
                 f"{evalues_fixed[i]:.0e}", va="center", ha="left",
                 fontsize=7, color="#1a1a1a")

    plt.tight_layout()
    chart_path = f"{RESULTS_DIR}/identity_chart.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    print(f"Chart saved to {chart_path}")
    plt.show()

def compare_species():
    print("\nFetching insulin sequences from other species...")
    species_ids = {
        "Rat":   "NM_012582",
        "Mouse": "NM_008386",
        "Pig":   "NM_214049",
        "Cow":   "NM_173932",
        "Dog":   "NM_001159779"
    }
    human_record = SeqIO.read(f"{RESULTS_DIR}/insulin_sequence.fasta", "fasta")
    human_seq = str(human_record.seq)
    comparison_results = []
    for species, accession in species_ids.items():
        print(f"Fetching {species} insulin ({accession})...")
        time.sleep(1)
        handle = Entrez.efetch(
            db="nucleotide",
            id=accession,
            rettype="fasta",
            retmode="text"
        )
        record = SeqIO.read(handle, "fasta")
        handle.close()
        animal_seq = str(record.seq)
        alignments = pairwise2.align.globalxx(
            human_seq[:500], animal_seq[:500],
            one_alignment_only=True
        )
        best = alignments[0]
        matches = best.score
        identity = round((matches / 500) * 100, 2)
        comparison_results.append({
            "species": species,
            "identity": identity,
            "seq_length": len(animal_seq)
        })
        print(f"{species}: {identity}% identity with human insulin")
    return comparison_results

def visualize_species_comparison(comparison_results):
    print("\nCreating species comparison chart...")
    species = [r["species"] for r in comparison_results]
    identities = [r["identity"] for r in comparison_results]
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#2ecc71" if i >= 90 else "#f39c12" if i >= 70 else "#e74c3c"
              for i in identities]
    bars = ax.barh(species, identities, color=colors, height=0.5)
    ax.set_xlabel("Identity % with Human Insulin", fontsize=12)
    ax.set_title("Human Insulin vs Other Mammals\nDirect Sequence Comparison",
                 fontsize=13, fontweight="bold")
    ax.set_xlim(0, 100)
    legend_elements = [
        Patch(facecolor="#2ecc71", label="Above 90% - Very similar"),
        Patch(facecolor="#f39c12", label="70-90% - Moderately similar"),
        Patch(facecolor="#e74c3c", label="Below 70% - Distantly related")
    ]
    ax.legend(handles=legend_elements, loc="lower right")
    for bar, val in zip(bars, identities):
        ax.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                f"{val}%", va="center", fontsize=10, fontweight="bold")
    plt.tight_layout()
    chart_path = f"{RESULTS_DIR}/species_comparison_chart.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    print(f"Species comparison chart saved!")
    plt.show()

def main():
    print("=" * 60)
    print("Human Insulin Gene - DNA Sequence Analysis")
    print("CodeAlpha Bioinformatics Internship - Task 1")
    print("=" * 60)

    # Step 1: Fetch human insulin sequence
    accession_id = "NM_000207"
    record = fetch_sequence(accession_id)
    time.sleep(2)

    # Step 2: Load BLAST results (skip if already saved)
    blast_xml = f"{RESULTS_DIR}/blast_results.xml"
    if not os.path.exists(blast_xml):
        blast_xml = run_blast(record)
    else:
        print("\nBLAST results already saved, loading from file...")

    # Step 3: Parse BLAST results
    results = parse_blast_results(blast_xml)

    # Step 4: Visualize BLAST results
    create_visualization(results)

    # Step 5: Compare with other mammals
    comparison_results = compare_species()

    # Step 6: Visualize species comparison
    visualize_species_comparison(comparison_results)

    print("\n" + "=" * 60)
    print("Analysis Complete!")
    print(f"All files saved in: {RESULTS_DIR}/")
    print("=" * 60)

if __name__ == "__main__":
    main()