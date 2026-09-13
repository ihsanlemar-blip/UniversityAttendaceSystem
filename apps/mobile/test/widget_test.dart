import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/main.dart';

void main() {
  testWidgets('Renders bootstrap shell successfully', (WidgetTester tester) async {
    await tester.pumpWidget(const AttendanceApp());

    expect(find.text('Digital Student Attendance System'), findsOneWidget);
    expect(find.text('Milestone 3 — Bootstrap Shell'), findsOneWidget);
  });
}
