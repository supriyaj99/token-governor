"""
corpus.py
---------
A tiny knowledge base for the RAG (Retrieval-Augmented Generation) demo.

RAG means: instead of hoping the model already knows the answer, we FIRST look
up relevant facts from our own documents, then hand those facts to the model
along with the question. This grounds answers in real data and is one of the
most in-demand AI skills in 2026.

In a real system these "documents" would be your company's wiki, product docs,
support tickets, etc., stored in a vector database. For a self-contained demo we
keep a few short documents here as plain text. Each one is a "chunk" the
retriever can match a question against.
"""

DOCUMENTS = [
    {
        "id": "returns",
        "text": "Acme's return policy allows customers to return any product "
                "within 30 days of delivery for a full refund. Items must be "
                "unused and in original packaging. Refunds are processed within "
                "5 business days of receiving the returned item.",
    },
    {
        "id": "shipping",
        "text": "Acme ships to over 40 countries. Standard shipping takes 5 to 7 "
                "business days. Express shipping takes 2 business days and costs "
                "an extra 15 dollars. Orders above 75 dollars get free standard "
                "shipping.",
    },
    {
        "id": "warranty",
        "text": "All Acme electronics come with a 2-year limited warranty "
                "covering manufacturing defects. The warranty does not cover "
                "accidental damage or water damage. Customers can file a warranty "
                "claim through the support portal.",
    },
    {
        "id": "accounts",
        "text": "Acme accounts are free to create. A Pro account costs 9 dollars "
                "per month and unlocks priority support and order tracking. "
                "Accounts can be cancelled anytime from the billing settings page.",
    },
    {
        "id": "support",
        "text": "Acme customer support is available Monday to Friday, 9am to 6pm. "
                "Pro members get 24/7 support. The fastest way to reach support is "
                "the live chat on the website.",
    },
    {
        "id": "payments",
        "text": "Acme accepts Visa, Mastercard, American Express, and PayPal. "
                "Payment is charged when the order ships, not when it is placed. "
                "Acme does not store full card numbers; payments are handled by a "
                "certified payment processor.",
    },
]
