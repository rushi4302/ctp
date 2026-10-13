import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/shared/utils/complaint_presentation.dart';

void main() {
  test('status values are presented as readable labels', () {
    expect(humanizeStatus('IN_PROGRESS'), 'In Progress');
    expect(humanizeStatus('NEEDS_ATTENTION'), 'Needs Attention');
  });

  test(
    'synthetic identifiers and seed disclaimer are removed only for demos',
    () {
      const title = '[SYNTHETIC DEMO DATASET V2 001] Blocked roadside drain';
      const description =
          'A drain is blocked. Location: near Kesnand Road, Wagholi, Pune. '
          'Synthetic demonstration record with approximate locality-center coordinates; '
          'not a citizen submission or verified municipal record.';

      expect(
        presentComplaintTitle(title, isSynthetic: true),
        'Blocked roadside drain',
      );
      expect(
        presentComplaintDescription(description, isSynthetic: true),
        'A drain is blocked. Location: near Kesnand Road, Wagholi, Pune.',
      );
      expect(presentComplaintTitle(title, isSynthetic: false), title);
    },
  );

  test(
    'demo assignments are cleanly labeled and missing metadata is explained',
    () {
      expect(
        presentDepartment('Drainage (synthetic assignment)', isSynthetic: true),
        'Drainage',
      );
      expect(
        locationMetadataNotice('MISSING_METADATA', isSynthetic: false),
        contains('photo did not include location metadata'),
      );
    },
  );
}
