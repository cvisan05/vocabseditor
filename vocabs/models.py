import os
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save, m2m_changed
from guardian.shortcuts import assign_perm, remove_perm
from django.dispatch import receiver
from django.contrib.auth.models import Permission
from guardian.shortcuts import get_objects_for_user
import reversion


try:
    DEFAULT_NAMESPACE = settings.VOCABS_SETTINGS['default_nsgg']
except KeyError:
    DEFAULT_NAMESPACE = "https://vocabs.acdh.oeaw.ac.at/provide-some-namespace"

try:
    DEFAULT_PREFIX = settings.VOCABS_SETTINGS['default_prefix']
except KeyError:
    DEFAULT_PREFIX = "provideSome"

try:
    DEFAULT_LANG = settings.VOCABS_SETTINGS['default_lang']
except KeyError:
    DEFAULT_LANG = "en"


LABEL_TYPES = (
    ('prefLabel', 'prefLabel'),
    ('altLabel', 'altLabel'),
    ('hiddenLabel', 'hiddenLabel'),
)

NOTE_TYPES = (
    ('note', 'note'),
    ('scopeNote', 'scopeNote'),
    ('changeNote', 'changeNote'),
    ('editorialNote', 'editorialNote'),
    ('historyNote', 'historyNote'),
    ('definition', 'definition'),
    ('example', 'example'),
)



######################################################################
#
# SkosConceptScheme
#
######################################################################

@reversion.register()
class SkosConceptScheme(models.Model):
    """
    A SKOS concept scheme can be viewed as an aggregation of one or more SKOS concepts.
    Semantic relationships (links) between those concepts
    may also be viewed as part of a concept scheme.

    Miles, Alistair, and Sean Bechhofer. "SKOS simple knowledge
    organization system reference. W3C recommendation (2009)."
    """
    dc_title = models.CharField(
        max_length=300, blank=True,
        help_text="Title of a Concept Scheme",
        verbose_name="dc:title"
    )
    dc_title_lang = models.CharField(
        max_length=3, blank=True,
        verbose_name="dc:title language", default=DEFAULT_LANG
    )
    indentifier = models.URLField(
        blank=True, default=DEFAULT_NAMESPACE,
        help_text="URI"
    )
    dc_creator = models.TextField(
        blank=True, verbose_name="dc:creator",
        help_text="If more than one list all using a semicolon ;"
    )
    dc_contributor = models.TextField(
        blank=True, verbose_name="dc:contributor",
        help_text="A Person or Organisation that made contributions to the vocabulary<br>"
        "If more than one list all using a semicolon ;"
    )
    dc_description = models.TextField(
        blank=True, verbose_name="dc:description",
        help_text="Description of current vocabulary"
    )
    dc_description_lang = models.CharField(
        max_length=3, blank=True,
        verbose_name="dc:description language",
        default=DEFAULT_LANG
    )
    dc_language = models.TextField(
        blank=True, verbose_name="dc:language",
        help_text="Language(s) used in Concept Scheme<br>"
        "If more than one list all using a semicolon ;"
    )
    dc_subject = models.TextField(
        blank=True, verbose_name="dc:subject",
        help_text="The subject of the vocabulary<br>"
        "If more than one list all using a semicolon ;"
    )
    version = models.CharField(
        max_length=300, blank=True,
        help_text="Current version"
    )
    dc_publisher = models.CharField(
        max_length=300, blank=True,
        help_text="An Organisation responsible for making the vocabulary available",
        verbose_name="dc:publisher"
    )
    dc_source = models.CharField(
        max_length=500, blank=True,
        help_text="A related resource a vocabulary based or derived from.",
        verbose_name="dc:source"
    )
    dc_rights = models.CharField(
        max_length=300, blank=True,
        verbose_name="dc:rights",
        help_text="Information about license or rights applied to a vocabulary"
    )
    owner = models.CharField(
        max_length=300, blank=True,
        help_text="A Person or Organisation that own rights for the vocabulary"
    )
    dc_relation = models.URLField(
        blank=True, verbose_name="dc:relation",
        help_text="E.g. in case of relation to a project, add link to a project website"
    )
    dc_coverage = models.TextField(
        blank=True, verbose_name="dc:coverage",
        help_text="The spatial or temporal coverage of a vocabulary<br>"
        "If more than one list all using a semicolon ;"
    )
    legacy_id = models.CharField(
        max_length=200, blank=True
    )
    date_created = models.DateTimeField(
        editable=False, default=timezone.now
    )
    date_modified = models.DateTimeField(
        editable=False, default=timezone.now
    )
    date_issued = models.DateField(
        blank=True, null=True,
        help_text="Date of official resource publication<br>YYYY-MM-DD"
    )
    created_by = models.ForeignKey(
        User, related_name="skos_cs_created",
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    curator = models.ManyToManyField(
        User, related_name="skos_cs_curated",
        blank=True,
        help_text="The selected user(s) will be able to view and edit current Concept Scheme."
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.date_created = timezone.now()
        self.date_modified = timezone.now()

        super(SkosConceptScheme, self).save(*args, **kwargs)

    def dc_creator_as_list(self):
        return self.dc_creator.split(';')

    def dc_contributor_as_list(self):
        return self.dc_contributor.split(';')

    def dc_language_as_list(self):
        return self.dc_language.split(';')

    def dc_subject_as_list(self):
        return self.dc_subject.split(';')

    def dc_coverage_as_list(self):
        return self.dc_coverage.split(';')

    @classmethod
    def get_listview_url(self):
        return reverse('vocabs:browse_schemes')

    @classmethod
    def get_createview_url(self):
        return reverse('vocabs:skosconceptscheme_create')

    def get_absolute_url(self):
        return reverse('vocabs:skosconceptscheme_detail', kwargs={'pk': self.id})

    def get_next(self):
        next = SkosConceptScheme.objects.filter(id__gt=self.id)
        if next:
            return next.first().id
        return False

    def get_prev(self):
        prev = SkosConceptScheme.objects.filter(id__lt=self.id).order_by('-id')
        if prev:
            return prev.first().id
        return False

    def __str__(self):
        if not self.dc_title:
            return self.id
        return self.dc_title


######################################################################
#   Classes  to store titles and descriptions for ConceptScheme
######################################################################

class ConceptSchemeTitle(models.Model):
    """
    A Class for ConceptScheme titles in other languages.
    
    """
    concept_scheme = models.ForeignKey(
        SkosConceptScheme,
        related_name="has_titles",
        verbose_name="skos:ConceptScheme",
        help_text="Which Skos:ConceptScheme current Title belongs to",
        on_delete=models.CASCADE
    )
    name = models.CharField(
        max_length=500, verbose_name="dc:title"
    )
    language = models.CharField(
        max_length=3
    )

    def __str__(self):
        return "{}".format(self.name)


class ConceptSchemeDescription(models.Model):
    """
    A Class for ConceptScheme descriptions in other languages.
    
    """
    concept_scheme = models.ForeignKey(
        SkosConceptScheme,
        related_name="has_descriptions",
        verbose_name="skos:ConceptScheme",
        help_text="Which Skos:ConceptScheme current Description belongs to",
        on_delete=models.CASCADE
    )
    name = models.TextField(
        verbose_name="dc:description"
    )
    language = models.CharField(
        max_length=3
    )

    def __str__(self):
        return self.name



######################################################################
#
# SkosCollection
#
######################################################################

@reversion.register()
class SkosCollection(models.Model):
    """
    SKOS collections are labeled and/or ordered groups of SKOS concepts.
    Collections are useful where a group of concepts shares something in common,
    and it is convenient to group them under a common label, or
    where some concepts can be placed in a meaningful order.

    Miles, Alistair, and Sean Bechhofer. "SKOS simple knowledge
    organization system reference. W3C recommendation (2009)."

    """
    name = models.CharField(
        max_length=300, blank=True, verbose_name="skos:prefLabel",
        help_text="Collection label or name"
    )
    label_lang = models.CharField(
        max_length=3, blank=True,
        default=DEFAULT_LANG,
        verbose_name="skos:prefLabel language"
    )
    # relation to SkosConceptScheme to inherit all objects permissions
    scheme = models.ForeignKey(SkosConceptScheme,
        related_name="has_collections",
        verbose_name="skos:ConceptScheme",
        help_text="Which Skos:ConceptScheme current collection belongs to",
        on_delete=models.CASCADE
    )
    creator = models.TextField(
        blank=True, verbose_name="dc:creator",
        help_text="A Person or Organisation that created a current collection<br>"
        "If more than one list all using a semicolon ;"
    )
    contributor = models.TextField(
        blank=True, verbose_name="dc:contributor",
        help_text="A Person or Organisation that made contributions to the collection<br>"
        "If more than one list all using a semicolon ;"
    )
    legacy_id = models.CharField(
        max_length=200, blank=True
    )
    # meta autosaved fields
    date_created = models.DateTimeField(
        editable=False, default=timezone.now
    )
    date_modified = models.DateTimeField(
        editable=False, default=timezone.now
    )
    created_by = models.ForeignKey(
        User, related_name="skos_collection_created",
        blank=True, null=True,
        on_delete=models.SET_NULL
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.date_created = timezone.now()
        self.date_modified = timezone.now()
        return super(SkosCollection, self).save(*args, **kwargs)

    @classmethod
    def get_listview_url(self):
        return reverse('vocabs:browse_skoscollections')

    @classmethod
    def get_createview_url(self):
        return reverse('vocabs:skoscollection_create')

    def get_absolute_url(self):
        return reverse('vocabs:skoscollection_detail', kwargs={'pk': self.id})

    def get_next(self):
        next = SkosCollection.objects.filter(id__gt=self.id)
        if next:
            return next.first().id
        return False

    def get_prev(self):
        prev = SkosCollection.objects.filter(id__lt=self.id).order_by('-id')
        if prev:
            return prev.first().id
        return False

    def __str__(self):
        if not self.name:
            return self.id
        return self.name

    def creator_as_list(self):
        return self.creator.split(';')

    def contributor_as_list(self):
        return self.contributor.split(';')


######################################################################
#   Classes  to store labels and notes for Collection
######################################################################


class CollectionLabel(models.Model):
    """
    A Class for Collection labels/names in other languages.
    
    """
    collection = models.ForeignKey(
        SkosCollection,
        related_name="has_labels",
        verbose_name="skos:Collection",
        help_text="Which Skos:Collection current label belongs to",
        on_delete=models.CASCADE
    )
    name = models.CharField(
        max_length=500, verbose_name="Label (Name)"
    )
    language = models.CharField(
        max_length=3
    )
    label_type = models.CharField(
        choices=LABEL_TYPES, default='altLabel',
        max_length=12
    )

    def __str__(self):
        return "{}".format(self.name)


class CollectionNote(models.Model):
    """
    A Class for SKOS documentary notes that are used
    for general documentation pusposes.

    """
    collection = models.ForeignKey(
        SkosCollection,
        related_name="has_notes",
        verbose_name="skos:Collection",
        help_text="Which Skos:Collection current documentary note belongs to",
        on_delete=models.CASCADE
    )
    name = models.TextField(
        verbose_name="Documentary note"
    )
    language = models.CharField(
        max_length=3
    )
    note_type = models.CharField(
        choices=NOTE_TYPES, default='note',
        max_length=15
    )

    def __str__(self):
        return "{}".format(self.name)


######################################################################
#
# SkosLabel
#
######################################################################

@reversion.register()
class SkosLabel(models.Model):
    """
    SKOS lexical labels are the expressions that are used to refer to concepts in natural language.

    Antoine Isaac and Ed Summers. "SKOS Simple Knowledge Organization System Primer.
    W3C Working Group Note (2009)."
    """
    name = models.CharField(
        max_length=100, blank=True, help_text="The entities label or name.",
        verbose_name="Label")
    label_type = models.CharField(
        max_length=30, blank=True, choices=LABEL_TYPES, 
        help_text="The type of the label.")
    # relation to SkosConceptScheme to inherit all objects permissions
    scheme = models.ForeignKey(SkosConceptScheme,
        related_name="has_labels",
        verbose_name="skos:ConceptScheme",
        help_text="Which Skos:ConceptScheme current collection belongs to",
        on_delete=models.CASCADE
    )
    isoCode = models.CharField(
        max_length=3, blank=True, help_text="The ISO 639-3 code for the label's language.")
    date_created = models.DateTimeField(
        editable=False, default=timezone.now
    )
    date_modified = models.DateTimeField(
        editable=False, default=timezone.now
    )
    created_by = models.ForeignKey(
        User, related_name="skos_label_created",
        blank=True, null=True,
        on_delete=models.SET_NULL
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.date_created = timezone.now()
        self.date_modified = timezone.now()

        if not self.label_type:
            self.label_type = "altLabel"
            
        return super(SkosLabel, self).save(*args, **kwargs)

    @classmethod
    def get_listview_url(self):
        return reverse('vocabs:browse_skoslabels')

    @classmethod
    def get_createview_url(self):
        return reverse('vocabs:skoslabel_create')

    def get_absolute_url(self):
        return reverse('vocabs:skoslabel_detail', kwargs={'pk': self.id})

    def get_next(self):
        next = SkosLabel.objects.filter(id__gt=self.id)
        if next:
            return next.first().id
        return False

    def get_prev(self):
        prev = SkosLabel.objects.filter(id__lt=self.id).order_by('-id')
        if prev:
            return prev.first().id
        return False

    def __str__(self):
        if self.label_type != "":
            return "{} @{} ({})".format(self.name, self.isoCode, self.label_type)
        else:
            return "{} @{}".format(self.name, self.isoCode)


######################################################################
#
# SkosConcept
#
######################################################################

@reversion.register()
class SkosConcept(models.Model):
    """
    A SKOS concept can be viewed as an idea or notion; a unit of thought.
    However, what constitutes a unit of thought is subjective,
    and this definition is meant to be suggestive, rather than restrictive.

    Miles, Alistair, and Sean Bechhofer. "SKOS simple knowledge
    organization system reference. W3C recommendation (2009)."
    """
    pref_label = models.CharField(
        max_length=300, blank=True,
        verbose_name="skos:prefLabel",
        help_text="Preferred label for a concept"
    )
    pref_label_lang = models.CharField(
        max_length=3, blank=True,
        verbose_name="skos:prefLabel language",
        help_text="Language code of preferred label according to ISO 639-3",
        default=DEFAULT_LANG
    )
    collection = models.ManyToManyField(
        SkosCollection, blank=True,
        verbose_name="member of skos:Collection",
        related_name="has_members",
    )
    # relation to SkosConceptScheme to inherit all objects permissions
    scheme = models.ForeignKey(
        SkosConceptScheme,
        verbose_name="skos:inScheme",
        related_name="has_concepts",
        on_delete=models.CASCADE,
        help_text="Main Concept Scheme"
    )
    definition = models.TextField(
        blank=True, verbose_name="skos:definition",
        help_text="Provide a complete explanation of the intended meaning of a concept"
    )
    definition_lang = models.CharField(
        max_length=3, blank=True,
        verbose_name="skos:definition language",
        default=DEFAULT_LANG
    )
    other_label = models.ManyToManyField(
        SkosLabel, blank=True,
        help_text="Select other labels that represent this concept"
    )
    notation = models.CharField(
        max_length=300, blank=True,
        verbose_name="skos:notation",
        help_text="A notation is a unique string used\
        to identify the concept in current vocabulary"
    )
    broader_concept = models.ForeignKey(
        'SkosConcept',
        verbose_name="Broader Term",
        blank=True, null=True, on_delete=models.SET_NULL,
        related_name="narrower_concepts",
        help_text="A concept with a broader meaning that a current concept inherits from"
    )
    top_concept = models.BooleanField(
        default=False,
        help_text="Is this concept a top concept of main Concept Scheme?"
    )
    same_as_external = models.TextField(
        blank=True,
        verbose_name="owl:sameAs",
        help_text="URL of an external Concept with the same meaning<br>"
        "If more than one list all using a semicolon ; ",
    )
    source_description = models.TextField(
        blank=True,
        verbose_name="Source",
        help_text="A verbose description of the concept's source"
    )
    skos_broader = models.ManyToManyField(
        'SkosConcept', blank=True, related_name="narrower",
        verbose_name="skos:broader",
        help_text="A concept with a broader meaning"
    )
    skos_narrower = models.ManyToManyField(
        'SkosConcept', blank=True, related_name="broader",
        verbose_name="skos:narrower",
        help_text="A concept with a narrower meaning"
    )
    skos_related = models.ManyToManyField(
        'SkosConcept', blank=True, related_name="related",
        verbose_name="skos:related",
        help_text="An associative relationship among two concepts"
    )
    skos_broadmatch = models.ManyToManyField(
        'SkosConcept', blank=True, related_name="narrowmatch",
        verbose_name="skos:broadMatch",
        help_text="A concept in an external ConceptSchema with a broader meaning"
    )
    skos_narrowmatch = models.ManyToManyField(
        'SkosConcept', blank=True, related_name="broadmatch",
        verbose_name="skos:narrowMatch",
        help_text="A concept in an external ConceptSchema with a narrower meaning"
    )
    skos_exactmatch = models.ManyToManyField(
        'SkosConcept', blank=True, related_name="exactmatch",
        verbose_name="skos:exactMatch",
        help_text="A concept in an external ConceptSchema "
        "that can be used interchangeably and has an exact same meaning"
    )
    skos_relatedmatch = models.ManyToManyField(
        'SkosConcept', blank=True, related_name="relatedmatch",
        verbose_name="skos:relatedMatch",
        help_text="A concept in an external ConceptSchema that has an associative "
        "relationship with a current concept"
    )
    skos_closematch = models.ManyToManyField(
        'SkosConcept', blank=True, related_name="closematch",
        verbose_name="skos:closeMatch",
        help_text="A concept in an external ConceptSchema that has a similar meaning"

    )
    legacy_id = models.CharField(max_length=200, blank=True)
    name_reverse = models.CharField(
        max_length=255,
        verbose_name="name reverse",
        help_text="Inverse relation like: \
        'is sub-class of' vs. 'is super-class of'.",
        blank=True
    )
    # documentation properties
    skos_note = models.CharField(
        max_length=500, blank=True,
        verbose_name="skos:note",
        help_text="Provide some partial information about the meaning of a concept"
    )
    skos_note_lang = models.CharField(
        max_length=3, blank=True,
        default=DEFAULT_LANG, verbose_name="skos:note language"
    )
    skos_scopenote = models.TextField(
        blank=True, verbose_name="skos:scopeNote",
        help_text="Provide more detailed information of the intended meaning of a concept"
    )
    skos_scopenote_lang = models.CharField(
        max_length=3, blank=True,
        default=DEFAULT_LANG, verbose_name="skos:scopeNote language"
    )
    skos_changenote = models.CharField(
        max_length=500, blank=True,
        verbose_name="skos:changeNote",
        help_text="Document any changes to a concept"
    )
    skos_editorialnote = models.CharField(
        max_length=500, blank=True,
        verbose_name="skos:editorialNote",
        help_text="Provide any administrative information, for the "
        "purposes of administration and maintenance. E.g. comments on "
        "reviewing this concept"
    )
    skos_example = models.CharField(
        max_length=500, blank=True,
        verbose_name="skos:example",
        help_text="Provide an example of a concept usage"
    )
    skos_historynote = models.CharField(
        max_length=500, blank=True,
        verbose_name="skos:historyNote",
        help_text="Describe significant changes to the meaning of a concept over a time"
    )
    # meta
    dc_creator = models.TextField(
        blank=True, verbose_name="dc:creator",
        help_text="A Person or Organisation that created a current concept<br>"
        "If more than one list all using a semicolon ;",

    )
    date_created = models.DateTimeField(
        editable=False, default=timezone.now,
        verbose_name="dct:created"
    )
    date_modified = models.DateTimeField(
        editable=False, default=timezone.now,
        verbose_name="dct:modified"
    )
    created_by = models.ForeignKey(
        User, related_name="skos_concept_created",
        blank=True, null=True,
        on_delete=models.SET_NULL
    )

    def get_broader(self):
        broader = self.skos_broader.all()
        broader_reverse = SkosConcept.objects.filter(skos_narrower=self)
        all_broader = set(list(broader)+list(broader_reverse))
        return all_broader

    def get_narrower(self):
        narrower = self.skos_narrower.all()
        narrower_reverse = SkosConcept.objects.filter(skos_broader=self)
        all_narrower = set(list(narrower)+list(narrower_reverse))
        return all_narrower

    def get_vocabs_uri(self):
        return "{}{}".format("https://whatever", self.get_absolute_url)

    @property
    def all_schemes(self):
        return ', '.join([x.dc_title for x in self.scheme.all()])

    def save(self, *args, **kwargs):
        if self.notation == "":
            temp_notation = slugify(self.pref_label, allow_unicode=True)
            concepts = len(SkosConcept.objects.filter(notation=temp_notation))
            if concepts < 1:
                self.notation = temp_notation
            else:
                self.notation = "{}-{}".format(temp_notation, concepts)
        else:
            pass

        if not self.id:
            self.date_created = timezone.now()
        self.date_modified = timezone.now()

        super(SkosConcept, self).save(*args, **kwargs)

    def dc_creator_as_list(self):
        return self.dc_creator.split(';')

    def same_as_external_as_list(self):
        return self.same_as_external.split(';')

    @cached_property
    def label(self):
        # 'borrowed from https://github.com/sennierer'
        d = self
        res = self.pref_label
        while d.broader_concept:
            res = d.broader_concept.pref_label + ' >> ' + res
            d = d.broader_concept
        return res

    @classmethod
    def get_listview_url(self):
        return reverse('vocabs:browse_vocabs')

    @classmethod
    def get_createview_url(self):
        return reverse('vocabs:skosconcept_create')

    def get_absolute_url(self):
        return reverse('vocabs:skosconcept_detail', kwargs={'pk': self.id})

    def get_next(self):
        next = SkosConcept.objects.filter(id__gt=self.id)
        if next:
            return next.first().id
        return False

    def get_prev(self):
        prev = SkosConcept.objects.filter(id__lt=self.id).order_by('-id')
        if prev:
            return prev.first().id
        return False

    def __str__(self):
        return self.pref_label


######################################################################
#   Classes  to store labels and notes for Concept
######################################################################


class ConceptLabel(models.Model):
    """
    A Class for Concept labels of any type.
    
    """
    concept = models.ForeignKey(
        SkosConcept,
        related_name="has_labels",
        verbose_name="skos:Concept",
        help_text="Which Skos:Concept current label belongs to",
        on_delete=models.CASCADE
    )
    name = models.CharField(
        max_length=500, verbose_name="Label"
    )
    language = models.CharField(
        max_length=3
    )
    label_type = models.CharField(
        choices=LABEL_TYPES, default='altLabel',
        max_length=12
    )

    def __str__(self):
        return "{}".format(self.name)
    

class ConceptNote(models.Model):
    """
    A Class for SKOS documentary notes that are used
    for general documentation pusposes.

    """
    concept = models.ForeignKey(
        SkosConcept,
        related_name="has_notes",
        verbose_name="skos:Concept",
        help_text="Which Skos:Concept current documentary note belongs to",
        on_delete=models.CASCADE
    )
    name = models.TextField(
        verbose_name="Documentary note"
    )
    language = models.CharField(
        max_length=3
    )
    note_type = models.CharField(
        choices=NOTE_TYPES, default='note',
        max_length=15
    )

    def __str__(self):
        return "{}".format(self.name)


class ConceptSource(models.Model):
    """
    A Class for Concept source information.
    
    """
    concept = models.ForeignKey(
        SkosConcept,
        related_name="has_sources",
        verbose_name="skos:Concept",
        help_text="Which Skos:Concept current source belongs to",
        on_delete=models.CASCADE
    )
    name = models.TextField(
        verbose_name="Source",
        help_text="A verbose description of the concept's source"
    )
    language = models.CharField(
        max_length=3
    )

    def __str__(self):
        return "{}".format(self.name)



def get_all_children(self, include_self=True):
    # many thanks to https://stackoverflow.com/questions/4725343
    r = []
    if include_self:
        r.append(self)
    for c in SkosConcept.objects.filter(broader_concept=self):
        _r = get_all_children(c, include_self=True)
        if 0 < len(_r):
            r.extend(_r)
    return r

#############################################################################
#
# Permissions on signals
#
#############################################################################


@receiver(post_save, sender=SkosConceptScheme, dispatch_uid="create_perms_cs_created_by")
def create_perms_cs_created_by(sender, instance, **kwargs):
    assign_perm('delete_skosconceptscheme', instance.created_by, instance)
    assign_perm('change_skosconceptscheme', instance.created_by, instance)
    assign_perm('view_skosconceptscheme', instance.created_by, instance)


@receiver(post_save, sender=SkosCollection, dispatch_uid="create_perms_collection_created_by")
def create_perms_collection_created_by(sender, instance, **kwargs):
    assign_perm('delete_skoscollection', instance.created_by, instance)
    assign_perm('change_skoscollection', instance.created_by, instance)
    assign_perm('view_skoscollection', instance.created_by, instance)
    for curator in instance.scheme.curator.all():
        assign_perm('delete_skoscollection', curator, instance)
        assign_perm('change_skoscollection', curator, instance)
        assign_perm('view_skoscollection', curator, instance)
        if curator is not instance.scheme.created_by:
            assign_perm('delete_skoscollection', instance.scheme.created_by, instance)
            assign_perm('change_skoscollection', instance.scheme.created_by, instance)
            assign_perm('view_skoscollection', instance.scheme.created_by, instance)


@receiver(post_save, sender=SkosConcept, dispatch_uid="create_perms_concept_created_by")
def create_perms_concept_created_by(sender, instance, **kwargs):
    assign_perm('delete_skosconcept', instance.created_by, instance)
    assign_perm('change_skosconcept', instance.created_by, instance)
    assign_perm('view_skosconcept', instance.created_by, instance)
    for curator in instance.scheme.curator.all():
        assign_perm('delete_skosconcept', curator, instance)
        assign_perm('change_skosconcept', curator, instance)
        assign_perm('view_skosconcept', curator, instance)
        if curator is not instance.scheme.created_by:
            assign_perm('delete_skosconcept', instance.scheme.created_by, instance)
            assign_perm('change_skosconcept', instance.scheme.created_by, instance)
            assign_perm('view_skosconcept', instance.scheme.created_by, instance)


@receiver(post_save, sender=SkosLabel, dispatch_uid="create_perms_label_created_by")
def create_perms_label_created_by(sender, instance, **kwargs):
    assign_perm('delete_skoslabel', instance.created_by, instance)
    assign_perm('change_skoslabel', instance.created_by, instance)
    assign_perm('view_skoslabel', instance.created_by, instance)
    for curator in instance.scheme.curator.all():
        assign_perm('delete_skoslabel', curator, instance)
        assign_perm('change_skoslabel', curator, instance)
        assign_perm('view_skoslabel', curator, instance)
        if curator is not instance.scheme.created_by:
            assign_perm('delete_skoslabel', instance.scheme.created_by, instance)
            assign_perm('change_skoslabel', instance.scheme.created_by, instance)
            assign_perm('view_skoslabel', instance.scheme.created_by, instance)


############### Adding new curator (user) to a Concept Scheme ###################
############### Only user who created a Concept Scheme can do it ################


@receiver(m2m_changed, sender=SkosConceptScheme.curator.through, dispatch_uid="create_perms_curator")
def create_perms_curator(sender, instance, **kwargs):
    if kwargs['action'] == 'pre_add':
        for curator in User.objects.filter(pk__in=kwargs['pk_set']):
            assign_perm('view_skosconceptscheme', curator, instance)
            assign_perm('change_skosconceptscheme', curator, instance)
            assign_perm('delete_skosconceptscheme', curator, instance)
            for obj in instance.has_collections.all():
                assign_perm('view_'+obj.__class__.__name__.lower(), curator, obj)
                assign_perm('change_'+obj.__class__.__name__.lower(), curator, obj)
                assign_perm('delete_'+obj.__class__.__name__.lower(), curator, obj)
            for obj in instance.has_concepts.all():
                assign_perm('view_'+obj.__class__.__name__.lower(), curator, obj)
                assign_perm('change_'+obj.__class__.__name__.lower(), curator, obj)
                assign_perm('delete_'+obj.__class__.__name__.lower(), curator, obj)
            for obj in instance.has_labels.all():
                assign_perm('view_'+obj.__class__.__name__.lower(), curator, obj)
                assign_perm('change_'+obj.__class__.__name__.lower(), curator, obj)
                assign_perm('delete_'+obj.__class__.__name__.lower(), curator, obj)
    elif kwargs['action'] == 'post_remove':
        for curator in User.objects.filter(pk__in=kwargs['pk_set']):
            remove_perm('view_skosconceptscheme', curator, instance)
            remove_perm('change_skosconceptscheme', curator, instance)
            # if user removed from the curators list
            # he/she won't be able to access the objects he/she created within this CS
            for obj in instance.has_collections.all():
                remove_perm('view_'+obj.__class__.__name__.lower(), curator, obj)
                remove_perm('change_'+obj.__class__.__name__.lower(), curator, obj)
                remove_perm('delete_'+obj.__class__.__name__.lower(), curator, obj)
            for obj in instance.has_concepts.all():
                remove_perm('view_'+obj.__class__.__name__.lower(), curator, obj)
                remove_perm('change_'+obj.__class__.__name__.lower(), curator, obj)
                remove_perm('delete_'+obj.__class__.__name__.lower(), curator, obj)
            for obj in instance.has_labels.all():
                remove_perm('view_'+obj.__class__.__name__.lower(), curator, obj)
                remove_perm('change_'+obj.__class__.__name__.lower(), curator, obj)
                remove_perm('delete_'+obj.__class__.__name__.lower(), curator, obj)