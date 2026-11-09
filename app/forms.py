from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class AdminLoginForm(FlaskForm):
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=4, max=128)])
    submit = SubmitField("Entrar")


class AddParticipantsForm(FlaskForm):
    names = TextAreaField(
        "Lista",
        validators=[DataRequired(), Length(min=1, max=20000)],
    )
    submit = SubmitField("Adicionar à lista")


class DrawByNameForm(FlaskForm):
    name = SelectField("Seu nome", validators=[DataRequired()], choices=[])
    access_password = PasswordField(
        "Senha de acesso",
        validators=[DataRequired(), Length(min=3, max=64)],
    )
    submit = SubmitField("Ver / Sortear")


class ConfirmForm(FlaskForm):
    submit = SubmitField("Confirmar")
