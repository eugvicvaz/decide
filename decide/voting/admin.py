from django.contrib import admin
from django.utils import timezone

from .models import *

from .filters import StartedFilter

#Votacion Preferencia
class PreferenceQuestionInline(admin.TabularInline):
    model = PreferenceQuestion
    extra = 1

class PreferenceVotingAdmin(admin.ModelAdmin):
    list_display=('id', 'name', 'desc', 'getNumberQuestions')
    inlines=[PreferenceQuestionInline]

class ResponseOptionInline(admin.TabularInline):
    model = ResponseOption
    extra = 1

class PreferenceQuestionAdmin(admin.ModelAdmin):
    list_display=('id', 'preferenceVoting', 'question', 'getNumberOptions')
    inlines=[ResponseOptionInline]

class PreferenceResponseInline(admin.TabularInline):
    model = PreferenceResponse
    extra = 1

class ResponseOptionAdmin(admin.ModelAdmin):
    list_display=('id', 'preferenceQuestion', 'option', 'getQuestion', 'preferenceAverage', 'responseOption')
    inlines=[PreferenceResponseInline]

class PreferenceResponseAdmin(admin.ModelAdmin):
    list_display=('id', 'responseOption', 'sortedPreference')
    

def start(modeladmin, request, queryset):
    for v in queryset.all():
        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()


def stop(ModelAdmin, request, queryset):
    for v in queryset.all():
        v.end_date = timezone.now()
        v.save()


def tally(ModelAdmin, request, queryset):
    for v in queryset.filter(end_date__lt=timezone.now()):
        token = request.session.get('auth-token', '')
        v.tally_votes(token)


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption


class QuestionAdmin(admin.ModelAdmin):
    inlines = [QuestionOptionInline]


class VotingAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')
    readonly_fields = ('start_date', 'end_date', 'pub_key',
                       'tally', 'postproc')
    date_hierarchy = 'start_date'
    list_filter = (StartedFilter,)
    search_fields = ('name', )

    actions = [ start, stop, tally ]


admin.site.register(Voting, VotingAdmin)
admin.site.register(Question, QuestionAdmin)

admin.site.register(PreferenceVoting, PreferenceVotingAdmin)
admin.site.register(PreferenceQuestion, PreferenceQuestionAdmin)
admin.site.register(ResponseOption, ResponseOptionAdmin)
admin.site.register(PreferenceResponse, PreferenceResponseAdmin)
