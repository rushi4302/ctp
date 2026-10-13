String humanizeStatus(String value) {
  final words = value.trim().replaceAll('_', ' ').split(RegExp(r'\s+'));
  return words
      .where((word) => word.isNotEmpty)
      .map(
        (word) => '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}',
      )
      .join(' ');
}

String humanizeComponentName(String value) => humanizeStatus(value);

String presentComplaintTitle(String value, {required bool isSynthetic}) {
  if (!isSynthetic) return value;
  return value
      .replaceFirst(
        RegExp(r'^\s*\[SYNTHETIC DEMO[^\]]*\]\s*', caseSensitive: false),
        '',
      )
      .trim();
}

String presentComplaintDescription(String value, {required bool isSynthetic}) {
  if (!isSynthetic) return value;
  return value
      .replaceAll(
        RegExp(
          r'\s*Synthetic demonstration record with approximate locality-center coordinates;\s*not a citizen submission or verified municipal record\.?\s*$',
          caseSensitive: false,
        ),
        '',
      )
      .trim();
}

String presentDepartment(String value, {required bool isSynthetic}) {
  var department = value.trim().replaceFirst(
    RegExp(r'^department:\s*', caseSensitive: false),
    '',
  );
  if (isSynthetic) {
    department = department.replaceFirst(
      RegExp(r'\s*\(synthetic assignment\)\s*$', caseSensitive: false),
      '',
    );
  }
  return department.trim();
}

String? locationMetadataNotice(String status, {required bool isSynthetic}) {
  switch (status.toUpperCase()) {
    case 'VALID':
      return null;
    case 'MISSING_METADATA':
      return isSynthetic
          ? 'Approximate demonstration location; the photo does not verify the map pin.'
          : 'The photo did not include location metadata, so the reported map pin could not be verified from the image.';
    case 'FLAGGED_FOR_REVIEW':
      return 'The reported location needs review.';
    case 'INVALID':
      return 'The reported location could not be verified.';
    default:
      return null;
  }
}
