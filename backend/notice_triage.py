from fastapi import HTTPException


def validate_resolution(original,body):
    if body["resolution"]=="addendum":
        if original["category"]!="wording":
            raise HTTPException(409,"口径数字或数据来源的异议须另查，文字补正不得直接改已签发布底")
        if not body["replacement_text"]:
            raise HTTPException(409,"发补正单须填写可公开的新措辞")
    elif body["replacement_text"]:
        raise HTTPException(409,"只有签发文字补正才附替代说明")
