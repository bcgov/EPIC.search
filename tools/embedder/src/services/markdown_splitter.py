from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def chunk_markdown_text(document_content):
    headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    ("####", "Header 4"),
    ("#####", "Header 5"),
    ("######", "Header 6"),
    ]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on,strip_headers = False)
    text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )
    text_markdown = splitter.split_text(document_content); 
    splited_text = text_splitter.split_documents(text_markdown)
    return splited_text