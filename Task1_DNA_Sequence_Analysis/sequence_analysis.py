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
    organisms = [r["organism"][:30] for r in results]
    identities = [r["identity"] for r in results]
    evalues = [r["evalue"] for r in results]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    fig.suptitle("Human Insulin Gene - BLAST Analysis Results",
                 fontsize=14, fontweight="bold")
    colors = ["#2ecc71" if i >= 90 else "#f39c12" if i >= 70 else "#e74c3c"
              for i in identities]
    bars = ax1.barh(organisms, identities, color=colors)
    ax1.set_xlabel("Identity %")
    ax1.set_title("Sequence Identity % Across Species")
    ax1.set_xlim(0, 100)
    ax1.axvline(x=90, color="green", linestyle="--", alpha=0.5, label="90% threshold")
    ax1.axvline(x=70, color="orange", linestyle="--", alpha=0.5, label="70% threshold")
    ax1.legend()
    for bar, val in zip(bars, identities):
        ax1.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                f"{val}%", va="center", fontsize=9)
    evalues_fixed = [max(e, 1e-200) for e in evalues]
    ax2.bar(range(len(organisms)), evalues_fixed, color="#3498db")
    ax2.set_xticks(range(len(organisms)))
    ax2.set_xticklabels(organisms, rotation=45, ha="right", fontsize=8)
    ax2.set_ylabel("E-value (log scale)")
    ax2.set_title("E-values for Each Match (lower = better)")
    ax2.set_yscale("log")
    ax2.set_ylim(1e-200, 1)
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