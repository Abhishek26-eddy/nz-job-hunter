import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def main():
    output = Path("/tmp/test_resume.pdf")
    c = canvas.Canvas(str(output), pagesize=letter)
    c.drawString(100, 700, "Jane Doe")
    c.drawString(100, 680, "Senior DevOps Engineer")
    c.drawString(100, 660, "Skills: Kubernetes, Terraform, AWS, Python, CI/CD")
    c.drawString(100, 640, "Experience: 8 years building cloud platforms")
    c.save()
    print(f"Created {output}")


if __name__ == "__main__":
    main()
