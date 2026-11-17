from rest_framework import serializers

from profiles.terms import format_term, parse_term


class PlanEntrySerializer(serializers.Serializer):
    term = serializers.CharField(max_length=20)
    course_code = serializers.CharField(max_length=30)
    counted_for = serializers.JSONField(required=False, default=None, allow_null=True)

    def validate_counted_for(self, value):
        if value is None:
            return None
        names = [value] if isinstance(value, str) else value
        if not isinstance(names, list) or any(
            not isinstance(name, str) or not name.strip() or len(name) > 255 for name in names
        ):
            raise serializers.ValidationError('Use a pool name, a list of pool names, or null.')
        if len(names) != len(set(names)):
            raise serializers.ValidationError('Pool names must be unique.')
        return value

    def validate_term(self, value):
        index = parse_term(value)
        if index is None:
            raise serializers.ValidationError('Use a term such as Spring 2028.')
        return format_term(index)

    def validate_course_code(self, value):
        return value.strip().upper()


class SavePlanSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    entries = PlanEntrySerializer(many=True, max_length=1000)

    def validate_entries(self, entries):
        codes = [entry['course_code'] for entry in entries]
        if len(codes) != len(set(codes)):
            raise serializers.ValidationError('A course can only appear once in a plan.')
        return entries
