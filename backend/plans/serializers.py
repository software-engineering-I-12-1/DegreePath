from rest_framework import serializers

from profiles.terms import format_term, parse_term


class PlanEntrySerializer(serializers.Serializer):
    term = serializers.CharField(max_length=20)
    course_code = serializers.CharField(max_length=30)

    def validate_term(self, value):
        index = parse_term(value)
        if index is None:
            raise serializers.ValidationError('Use a term such as Spring 2028.')
        return format_term(index)

    def validate_course_code(self, value):
        return value.strip().upper()


class SavePlanSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    entries = PlanEntrySerializer(many=True, allow_empty=False, max_length=1000)

    def validate_entries(self, entries):
        codes = [entry['course_code'] for entry in entries]
        if len(codes) != len(set(codes)):
            raise serializers.ValidationError('A course can only appear once in a plan.')
        return entries
