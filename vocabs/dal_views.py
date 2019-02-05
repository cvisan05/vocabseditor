from dal import autocomplete
from .models import SkosConcept, SkosConceptScheme, SkosCollection
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user
from django.contrib.auth.models import User
from mptt.settings import DEFAULT_LEVEL_INDICATOR


class SpecificConcepts(autocomplete.Select2QuerySetView):

    def get_result_label(self, item):
        return "{}".format(item.label)

    def get_queryset(self):
        try:
            scheme = self.kwargs['scheme']
            selected_scheme = SkosConceptScheme.objects.filter(title__icontains=scheme)
        except KeyError:
            selected_scheme = None
        if selected_scheme:
            qs = get_objects_for_user(self.request.user,
            'view_skosconcept',
            klass=SkosConcept)
            qs = qs.filter(scheme__in=selected_scheme)
        else:
            qs = get_objects_for_user(self.request.user,
            'view_skosconcept',
            klass=SkosConcept)

        if self.q:
            direct_match = qs.filter(pref_label__icontains=self.q)
            plus_narrower = direct_match | qs.filter(broader_concept__in=direct_match)
            return plus_narrower

        return []


class SKOSConstraintACNoHierarchy(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        scheme = self.request.GET.get('scheme')
        try:
            selected_scheme = SkosConceptScheme.objects.get(title=scheme)
            qs = SkosConcept.objects.filter(scheme=selected_scheme)
        except:
            qs = SkosConcept.objects.all()

        if self.q:
            qs = qs.filter(
                Q(pref_label__icontains=self.q)
            )

        return qs


class SkosConceptAC(autocomplete.Select2QuerySetView):

    def get_result_label(self, item):
        return "{}".format(item.label)

    def get_queryset(self):
        qs = get_objects_for_user(self.request.user,
            'view_skosconcept',
            klass=SkosConcept)
        #qs = SkosConcept.objects.all()
        if self.q:
            direct_match = qs.filter(pref_label__icontains=self.q)
            plus_narrower = qs.filter(broader_concept__in=direct_match) | direct_match
            return plus_narrower
        else:
            return qs


class SkosConceptNoBroaderTermAC(autocomplete.Select2QuerySetView):

    def get_result_label(self, item):
        level_indicator = DEFAULT_LEVEL_INDICATOR * item.level
        return level_indicator + ' ' + str(item)

    def get_queryset(self):
        qs = get_objects_for_user(self.request.user,
            'view_skosconcept',
            klass=SkosConcept)
        scheme = self.forwarded.get('scheme', None)
        if scheme:
            qs = qs.filter(scheme=scheme)
        if self.q:
            qs = qs.filter(pref_label__icontains=self.q)
        return qs


class SkosConceptExternalMatchAC(autocomplete.Select2QuerySetView):

    def get_result_label(self, item):
        level_indicator = DEFAULT_LEVEL_INDICATOR * item.level
        return level_indicator + ' ' + str(item)

    def get_queryset(self):
        qs = get_objects_for_user(self.request.user,
            'view_skosconcept',
            klass=SkosConcept)
        scheme = self.forwarded.get('scheme', None)
        if scheme:
            qs = qs.exclude(scheme=scheme)
        if self.q:
            qs = qs.filter(pref_label__icontains=self.q)
        return qs


class SkosConceptPrefLabalAC(autocomplete.Select2ListView):

    def get_list(self):
        concepts = SkosConcept.objects.filter(pref_label__icontains=self.q)
        pref_labels = set([x.pref_label for x in concepts])
        return pref_labels


class SkosConceptSchemeAC(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = get_objects_for_user(self.request.user,
            'view_skosconceptscheme',
            klass=SkosConceptScheme)
        #qs = SkosConceptScheme.objects.all()

        if self.q:
            qs = qs.filter(title__icontains=self.q)

        return qs


class SkosCollectionAC(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = get_objects_for_user(self.request.user,
            'view_skoscollection',
            klass=SkosCollection)
        scheme = self.forwarded.get('scheme', None)
        if scheme:
            qs = qs.filter(scheme=scheme)

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


class UserAC(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = User.objects.exclude(username=self.request.user)
        if self.q:
            qs = qs.filter(username__icontains=self.q)

        return qs
