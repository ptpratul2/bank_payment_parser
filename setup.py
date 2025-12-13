from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="bank_payment_parser",
    version="1.0.0",
    description="Scalable bank payment advice PDF parser with customer-specific parsing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Frappe",
    author_email="support@frappe.io",
    license="MIT",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        "pdfminer.six>=20221105",
    ],
    extras_require={
        "ocr": [
            "pytesseract>=0.3.10",
            "pdf2image>=1.16.3",
            "Pillow>=10.0.0",
        ],
    },
)
