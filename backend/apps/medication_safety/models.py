import uuid

from django.db import models
from django.db.models.functions import Now


class DrugIngredient(models.Model):
    """
    DB-019: drug_ingredients
    식품의약품안전처 DUR 성분 Master.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dur_ingredient_code = models.CharField(
        max_length=80,
        unique=True,
    )

    name_ko = models.CharField(
        max_length=200,
        db_index=True,
    )

    name_en = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )

    source_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_default=Now(),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=Now(),
    )

    class Meta:
        db_table = "drug_ingredients"
        verbose_name = "DUR 성분"
        verbose_name_plural = "DUR 성분"

    def __str__(self):
        return f"{self.dur_ingredient_code} - {self.name_ko}"


class DURInteractionRule(models.Model):
    """
    DB-021: dur_interaction_rules
    병용금기 규칙.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dur_seq = models.CharField(
        max_length=100,
        unique=True,
    )

    ingredient_a = models.ForeignKey(
        DrugIngredient,
        on_delete=models.PROTECT,
        related_name="interaction_rules_as_a",
        db_column="ingredient_a_id",
    )

    ingredient_b = models.ForeignKey(
        DrugIngredient,
        on_delete=models.PROTECT,
        related_name="interaction_rules_as_b",
        db_column="ingredient_b_id",
    )

    description = models.TextField()

    source_payload = models.JSONField(default=dict, blank=True)

    source = models.CharField(
        max_length=50,
        default="MFDS_DUR",
        db_default="MFDS_DUR",
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )

    source_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_default=Now(),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=Now(),
    )

    class Meta:
        db_table = "dur_interaction_rules"
        verbose_name = "DUR 병용금기 규칙"
        verbose_name_plural = "DUR 병용금기 규칙"

        indexes = [
            models.Index(
                fields=["ingredient_a", "ingredient_b"],
                name="dur_interaction_pair_idx",
            ),
        ]

    def __str__(self):
        return self.dur_seq


class DURDoseRule(models.Model):
    """
    DB-022: dur_dose_rules
    용량주의 규칙.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dur_seq = models.CharField(
        max_length=100,
        unique=True,
    )

    ingredient = models.ForeignKey(
        DrugIngredient,
        on_delete=models.PROTECT,
        related_name="dose_rules",
        db_column="ingredient_id",
    )

    max_dose = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )

    dose_unit = models.CharField(
        max_length=30,
        null=True,
        blank=True,
    )

    period = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    description = models.TextField()

    form_name = models.CharField(max_length=200, blank=True, default="")
    source_payload = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )

    source_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=Now(),
    )

    class Meta:
        db_table = "dur_dose_rules"
        verbose_name = "DUR 용량주의 규칙"
        verbose_name_plural = "DUR 용량주의 규칙"

    def __str__(self):
        return self.dur_seq


class DURDuplicateRule(models.Model):
    """
    DB-023: dur_duplicate_rules
    효능군 중복주의 규칙.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dur_seq = models.CharField(
        max_length=100,
        unique=True,
    )

    ingredient = models.ForeignKey(
        DrugIngredient,
        on_delete=models.PROTECT,
        related_name="duplicate_rules",
        db_column="ingredient_id",
    )

    therapeutic_class_code = models.CharField(
        max_length=100,
        db_index=True,
    )

    therapeutic_class_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        db_index=True,
    )

    description = models.TextField()

    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )

    source_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=Now(),
    )

    class Meta:
        db_table = "dur_duplicate_rules"
        verbose_name = "DUR 효능군 중복 규칙"
        verbose_name_plural = "DUR 효능군 중복 규칙"

    def __str__(self):
        return self.dur_seq


class DURAgeRule(models.Model):
    """
    DB-024: dur_age_rules
    특정연령 금기 규칙.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dur_seq = models.CharField(
        max_length=100,
        unique=True,
    )

    ingredient = models.ForeignKey(
        DrugIngredient,
        on_delete=models.PROTECT,
        related_name="age_rules",
        db_column="ingredient_id",
    )

    min_age = models.SmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )

    max_age = models.SmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )

    description = models.TextField()

    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )

    source_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=Now(),
    )

    class Meta:
        db_table = "dur_age_rules"
        verbose_name = "DUR 특정연령금기 규칙"
        verbose_name_plural = "DUR 특정연령금기 규칙"

    def __str__(self):
        return self.dur_seq


class DURElderlyRule(models.Model):
    """
    DB-025: dur_elderly_rules
    노인주의 규칙.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dur_seq = models.CharField(
        max_length=100,
        unique=True,
    )

    ingredient = models.ForeignKey(
        DrugIngredient,
        on_delete=models.PROTECT,
        related_name="elderly_rules",
        db_column="ingredient_id",
    )

    age_threshold = models.SmallIntegerField(
        default=65,
        db_default=65,
        db_index=True,
    )

    description = models.TextField()

    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )

    source_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=Now(),
    )

    class Meta:
        db_table = "dur_elderly_rules"
        verbose_name = "DUR 노인주의 규칙"
        verbose_name_plural = "DUR 노인주의 규칙"

    def __str__(self):
        return self.dur_seq


class DURPregnancyRule(models.Model):
    """
    DB-026: dur_pregnancy_rules
    임부금기 규칙.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dur_seq = models.CharField(
        max_length=100,
        unique=True,
    )

    ingredient = models.ForeignKey(
        DrugIngredient,
        on_delete=models.PROTECT,
        related_name="pregnancy_rules",
        db_column="ingredient_id",
    )

    pregnancy_grade = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True,
    )

    description = models.TextField()

    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )

    source_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=Now(),
    )

    class Meta:
        db_table = "dur_pregnancy_rules"
        verbose_name = "DUR 임부금기 규칙"
        verbose_name_plural = "DUR 임부금기 규칙"

    def __str__(self):
        return self.dur_seq

class DURDurationRule(models.Model):
    """
    DUR 투여기간주의 규칙.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dur_seq = models.CharField(
        max_length=100,
        unique=True,
    )

    ingredient = models.ForeignKey(
        DrugIngredient,
        on_delete=models.PROTECT,
        related_name="duration_rules",
        db_column="ingredient_id",
    )

    max_duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )

    max_duration_raw = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    form_name = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    description = models.TextField()

    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )

    source_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=Now(),
    )

    class Meta:
        db_table = "dur_duration_rules"
        verbose_name = "DUR 투여기간주의 규칙"
        verbose_name_plural = "DUR 투여기간주의 규칙"

    def __str__(self):
        return self.dur_seq


# === FINAL_DB_GENERATED_IMPORTS_START ===
from .models_generated import MedicationIngredient, PatientAllergy, MedicationSafetyOverride
# === FINAL_DB_GENERATED_IMPORTS_END ===
