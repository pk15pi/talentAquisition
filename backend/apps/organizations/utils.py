from django.db import IntegrityError, transaction
from .models import CodeSequence
def next_business_code(key: str, prefix: str, width: int = 4) -> str:
    with transaction.atomic():
        try:
            sequence=CodeSequence.objects.select_for_update().get(key=key)
        except CodeSequence.DoesNotExist:
            try:
                with transaction.atomic():
                    sequence=CodeSequence.objects.create(key=key,current_value=0)
            except IntegrityError:
                sequence=CodeSequence.objects.select_for_update().get(key=key)
        sequence.current_value += 1
        sequence.save(update_fields=["current_value"])
        return f"{prefix}{sequence.current_value:0{width}d}"
