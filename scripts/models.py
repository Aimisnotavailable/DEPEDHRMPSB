from flask_sqlalchemy import SQLAlchemy

class ModelDB:

    def __init__(self, app):
        self.db = SQLAlchemy(app)
        
        class ModelHandler:
            def get_model(self, model_type):
                if model_type == "interviews":
                    return Interview()
                elif model_type == "evaluator_tokens":
                    return EvaluatorToken()
                elif model_type == "Participant":
                    return Participant()
                elif model_type == "validations":
                    return Validation()
        
        self.model_handler = ModelHandler()
    # -----------------------------------------------------------------------------
    # Models
    # -----------------------------------------------------------------------------
        class Interview(self.db.Model):
            __tablename__ = "interviews"
            id       = self.db.Column(self.db.String(8), primary_key=True)
            base_edu = self.db.Column(self.db.Integer, nullable=False)
            base_exp = self.db.Column(self.db.Integer, nullable=False)
            base_trn = self.db.Column(self.db.Integer, nullable=False)
            # participants & evaluator_tokens backrefs are automatically injected

        class EvaluatorToken(self.db.Model):
            __tablename__ = "evaluator_tokens"
            token        = self.db.Column(self.db.String(8), primary_key=True)
            interview_id = self.db.Column(self.db.String(8), self.db.ForeignKey("interviews.id"), nullable=False)
            # Instead of storing evaluator's name, we mark the token as registered when used.
            registered   = self.db.Column(self.db.Boolean, default=False, nullable=False)
            interview    = self.db.relationship("Interview", backref="evaluator_tokens")

        class Participant(self.db.Model):
            __tablename__ = "participants"
            code          = self.db.Column(self.db.String(8), primary_key=True)
            interview_id  = self.db.Column(self.db.String(8), self.db.ForeignKey("interviews.id"), nullable=False)
            interview     = self.db.relationship("Interview", backref="participants")
            name          = self.db.Column(self.db.String(128), nullable=False)
            address       = self.db.Column(self.db.String(256), nullable=False)
            birthday      = self.db.Column(self.db.Date, nullable=False)
            age           = self.db.Column(self.db.Integer, nullable=False)
            sex           = self.db.Column(self.db.String(16), nullable=False)
            raw_edu       = self.db.Column(self.db.Integer, nullable=False)
            raw_exp       = self.db.Column(self.db.Integer, nullable=False)
            raw_trn       = self.db.Column(self.db.Integer, nullable=False)
            score_edu     = self.db.Column(self.db.Integer, nullable=False)
            score_exp     = self.db.Column(self.db.Integer, nullable=False)
            score_trn     = self.db.Column(self.db.Integer, nullable=False)

        class Validation(self.db.Model):
            __tablename__ = "validations"
            id                = self.db.Column(self.db.Integer, primary_key=True)
            interview_id      = self.db.Column(self.db.String(8), self.db.ForeignKey("interviews.id"), nullable=False)
            evaluator_token   = self.db.Column(self.db.String(8), self.db.ForeignKey("evaluator_tokens.token"), nullable=False)
            participant_code  = self.db.Column(self.db.String(8), self.db.ForeignKey("participants.code"),  nullable=False)
            comment           = self.db.Column(self.db.Text, nullable=True)

