import markdown

class ResponseFormatter:
    """Service dédié à la mise en forme des messages pour Matrix (Refactoring: Extract Class)."""
    
    @staticmethod
    def format(text: str) -> dict:
        """Retourne un dictionnaire prêt pour content['formatted_body']."""
        if not text:
            return {"body": "", "formatted_body": ""}
            
        html = markdown.markdown(
            text, 
            extensions=['extra', 'codehilite', 'nl2br']
        )
        
        return {
            "msgtype": "m.text",
            "body": text,
            "format": "org.matrix.custom.html",
            "formatted_body": html
        }
