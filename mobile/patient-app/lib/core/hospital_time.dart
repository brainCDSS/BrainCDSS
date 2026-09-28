/// Hospital-wide presentation timezone (KST), independent of device timezone.
DateTime? hospitalTime(DateTime? value) {
  if (value == null) return null;
  return value.toUtc().add(const Duration(hours: 9));
}
