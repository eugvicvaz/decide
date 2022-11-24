from django.db import models
from django.contrib.postgres.fields import JSONField
from django.db.models.signals import post_save
from django.dispatch import receiver

from base import mods
from base.models import Auth, Key

#Votacion por preferencia
class PreferenceVoting(models.Model):
    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True, null=True)
    id = models.AutoField(primary_key=True)

    def __str__(self):
        return self.name

    #Metodo que cuenta el numero de preguntas que contiene la votacion
    def getNumberQuestions(self):
        return PreferenceQuestion.objects.filter(preferenceVoting_id=self.id).count()

    #Metodo que añade preguntas por preferencia
    def addPreferenceQuestion(self, preferenceQuestion):
        preferenceQuestion.preferenceVoting = self
        preferenceQuestion.save()

class PreferenceQuestion(models.Model):
    id = models.AutoField(primary_key=True)
    preferenceVoting = models.ForeignKey(PreferenceVoting, on_delete=models.CASCADE)
    question = models.CharField(max_length=50)

    def __str__(self):
        return self.question

    def getVotingName(self):
        return self.preferenceVoting.name

    #Metodo que devuelve el numero de opciones de la pregunta
    def getNumberOptions(self):
        return ResponseOption.objects.filter(preferenceQuestion_id = self.id).count()
    
    #Metodo que añade una opcion a la pregunta
    def addResponseOption(self, responseOption):
        responseOption.preferenceVoting = self
        responseOption.save()

class ResponseOption(models.Model):
    id = models.AutoField(primary_key=True)
    preferenceQuestion = models.ForeignKey(PreferenceQuestion, on_delete=models.CASCADE)
    option = models.CharField(max_length=100)
    
    def __str__(self):
        return self.option

    def getQuestion(self):
        return self.preferenceQuestion.question

    #Metodo que añade respuesta a las preguntas
    def addResponse(self, preferenceResponse):
        preferenceResponse.responseOption = self
        preferenceResponse.save()

    #Metodo que devuelve la media de votos
    def preferenceAverage(self):
        responses = PreferenceResponse.objects.filter(responseOption_id=self.id).values('sortedPreference')
        numResponses = len(responses)
        if numResponses == 0:
            numResponses == 1
        total = 0
        for value in responses:
            total = total + value['sortedPreference']
        
        return total / numResponses

    def responseOption(self):
        responses = PreferenceResponse.objects.filter(responseOption_id=self.id).values('sortedPreference')
        res = {}

        for value in responses:
            if value['sortedPreference'] in res:
                result[value['sortedPreference']] = result[value['sortedPreference']] + 1
            else:
                result[value['sortedPreference']] = 1
        for key in res:
            res[key] = str(res[key]) + " veces"
        
        print(res)
        return sorted(res.items())


class PreferenceResponse(models.Model):
    id = models.AutoField(primary_key=True)
    responseOption = models.ForeignKey(ResponseOption, on_delete = models.CASCADE)
    sortedPreference = models.PositiveIntegerField(blank=True, null=True)

    def getName(self):
        return self.responseOption.option


#Votacion original de Decide
class Question(models.Model):
    desc = models.TextField()

    def __str__(self):
        return self.desc


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    number = models.PositiveIntegerField(blank=True, null=True)
    option = models.TextField()

    def save(self):
        if not self.number:
            self.number = self.question.options.count() + 2
        return super().save()

    def __str__(self):
        return '{} ({})'.format(self.option, self.number)


class Voting(models.Model):
    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True, null=True)
    question = models.ForeignKey(Question, related_name='voting', on_delete=models.CASCADE)

    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)

    pub_key = models.OneToOneField(Key, related_name='voting', blank=True, null=True, on_delete=models.SET_NULL)
    auths = models.ManyToManyField(Auth, related_name='votings')

    tally = JSONField(blank=True, null=True)
    postproc = JSONField(blank=True, null=True)

    def create_pubkey(self):
        if self.pub_key or not self.auths.count():
            return

        auth = self.auths.first()
        data = {
            "voting": self.id,
            "auths": [ {"name": a.name, "url": a.url} for a in self.auths.all() ],
        }
        key = mods.post('mixnet', baseurl=auth.url, json=data)
        pk = Key(p=key["p"], g=key["g"], y=key["y"])
        pk.save()
        self.pub_key = pk
        self.save()

    def get_votes(self, token=''):
        # gettings votes from store
        votes = mods.get('store', params={'voting_id': self.id}, HTTP_AUTHORIZATION='Token ' + token)
        # anon votes
        return [[i['a'], i['b']] for i in votes]

    def tally_votes(self, token=''):
        '''
        The tally is a shuffle and then a decrypt
        '''

        votes = self.get_votes(token)

        auth = self.auths.first()
        shuffle_url = "/shuffle/{}/".format(self.id)
        decrypt_url = "/decrypt/{}/".format(self.id)
        auths = [{"name": a.name, "url": a.url} for a in self.auths.all()]

        # first, we do the shuffle
        data = { "msgs": votes }
        response = mods.post('mixnet', entry_point=shuffle_url, baseurl=auth.url, json=data,
                response=True)
        if response.status_code != 200:
            # TODO: manage error
            pass

        # then, we can decrypt that
        data = {"msgs": response.json()}
        response = mods.post('mixnet', entry_point=decrypt_url, baseurl=auth.url, json=data,
                response=True)

        if response.status_code != 200:
            # TODO: manage error
            pass

        self.tally = response.json()
        self.save()

        self.do_postproc()

    def do_postproc(self):
        tally = self.tally
        options = self.question.options.all()

        opts = []
        for opt in options:
            if isinstance(tally, list):
                votes = tally.count(opt.number)
            else:
                votes = 0
            opts.append({
                'option': opt.option,
                'number': opt.number,
                'votes': votes
            })

        data = { 'type': 'IDENTITY', 'options': opts }
        postp = mods.post('postproc', json=data)

        self.postproc = postp
        self.save()

    def __str__(self):
        return self.name
