import pathlib

from bs4 import BeautifulSoup


def get_stylesheet() -> str:
    return """
    :root, [data-md-color-scheme="default"], body {
        --md-text-font-family: BlinkMacSystemFont, Helvetica, Arial, sans-serif;
        --md-code-font-family: SFMono-Regular,Consolas,Menlo,monospace;
    }
    @page {
        size: a4;
        font-family: BlinkMacSystemFont, Helvetica, Arial, sans-serif;
        @top-center {
            background: url("file://""" + str(pathlib.Path(__file__).parent.resolve()) + """/docs/pure.svg") no-repeat;
            background-position: 5% center;
            background-size:10%;
            content: 'Pure Storage Checkmk plugin';
            padding-left: 10%;
        }
    }
    figure, figure p {
        display: block;
        text-align: center;
    }
    """


def modify_html(html: str, href: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    soup.find("a", {"class": "md-social__link", "href": "%pdf%"})["href"] = href
    return str(soup)
