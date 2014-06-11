from flask.ext.wtf import Form
from wtforms import TextField, SelectField
from wtforms.validators import Required

people = ['Joe', 'Dan', 'Steph', 'Rachel', 'Charles']
people = zip(people, people)

class NewGameForm(Form):
    an_input = TextField('some input', validators = [Required()])
    player = SelectField('Player', choices = people)
