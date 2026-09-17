import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/core/api_client.dart';
import 'package:university_attendance_mobile/core/i18n/app_language.dart';
import 'package:university_attendance_mobile/core/i18n/app_strings.dart';
import 'package:university_attendance_mobile/core/i18n/translations_en.dart';
import 'package:university_attendance_mobile/core/i18n/translations_fa.dart';
import 'package:university_attendance_mobile/core/i18n/translations_ps.dart';
import 'package:university_attendance_mobile/screens/student_home_screen.dart';

void main() {
  group('AppLanguage and RTL Directives Tests', () {
    test('English language is configured as LTR', () {
      expect(AppLanguage.en.code, 'en');
      expect(AppLanguage.en.isRtl, isFalse);
      expect(AppLanguage.en.textDirection, TextDirection.ltr);
    });

    test('Dari (fa) language is configured as RTL with Afghan locale', () {
      expect(AppLanguage.fa.code, 'fa');
      expect(AppLanguage.fa.isRtl, isTrue);
      expect(AppLanguage.fa.textDirection, TextDirection.rtl);
      expect(AppLanguage.fa.locale, const Locale('fa', 'AF'));
    });

    test('Pashto (ps) language is configured as RTL with Afghan locale', () {
      expect(AppLanguage.ps.code, 'ps');
      expect(AppLanguage.ps.isRtl, isTrue);
      expect(AppLanguage.ps.textDirection, TextDirection.rtl);
      expect(AppLanguage.ps.locale, const Locale('ps', 'AF'));
    });
  });

  group('Afghan Academic Terminology Verification (No Iranian Substitutions)',
      () {
    test('Dari translations use authentic Afghan academic terms', () {
      // Must use Afghan academic terms
      expect(translationsFa['academic_university'], 'پوهنتون');
      expect(translationsFa['academic_faculty'], 'پوهنځی');
      expect(translationsFa['academic_department'], contains('څانګه'));
      expect(translationsFa['academic_credit'], 'کریدت');
      expect(translationsFa['academic_semester'], 'سمستر');
      expect(translationsFa['academic_morning_shift'], 'تایم سهارنی');
      expect(translationsFa['academic_afternoon_shift'], 'تایم بعد از ظهر');

      // Attendance status terms
      expect(translationsFa['status_present'], 'حاضر');
      expect(translationsFa['status_late'], 'ناوخته');
      expect(translationsFa['status_absent'], 'غیرحاضر');
      expect(translationsFa['status_excused'], 'معذور');

      // Strictly must NOT use Iranian-specific academic substitutions
      final allValues = translationsFa.values.join(' ');
      expect(allValues.contains('دانشگاه'), isFalse,
          reason: 'Must use پوهنتون, not Iranian دانشگاه');
      expect(allValues.contains('دانشکده'), isFalse,
          reason: 'Must use پوهنځی, not Iranian دانشکده');
    });

    test('Pashto translations use authentic Afghan academic terms', () {
      expect(translationsPs['academic_university'], 'پوهنتون');
      expect(translationsPs['academic_faculty'], 'پوهنځی');
      expect(translationsPs['academic_department'], 'څانګه');
      expect(translationsPs['academic_credit'], 'کریدت');
      expect(translationsPs['academic_semester'], 'سمستر');
      expect(translationsPs['academic_morning_shift'], 'سهارنی تایم');
      expect(translationsPs['academic_afternoon_shift'], 'ماسپښین تایم');

      // Attendance status terms
      expect(translationsPs['status_present'], 'حاضر');
      expect(translationsPs['status_late'], 'ناوخته');
      expect(translationsPs['status_absent'], 'غیرحاضر');
      expect(translationsPs['status_excused'], 'معذور');

      final allValues = translationsPs.values.join(' ');
      expect(allValues.contains('دانشگاه'), isFalse);
      expect(allValues.contains('دانشکده'), isFalse);
    });

    test('Dictionary parity: all English keys exist in Dari and Pashto', () {
      for (final key in translationsEn.keys) {
        expect(translationsFa.containsKey(key), isTrue,
            reason: 'Missing Dari translation for key: $key');
        expect(translationsPs.containsKey(key), isTrue,
            reason: 'Missing Pashto translation for key: $key');
      }
    });
  });

  group('Safe Error Message Resolver Tests', () {
    test(
        'Translates standard backend error codes without leaking DB/SQL internals',
        () {
      final stringsEn = AppStrings.get(AppLanguage.en);
      final stringsFa = AppStrings.get(AppLanguage.fa);
      final stringsPs = AppStrings.get(AppLanguage.ps);

      final errorCodes = [
        'TOKEN_EXPIRED',
        'CHECKPOINT_NOT_OPEN',
        'SESSION_CLOSED',
        'DEVICE_NOT_REGISTERED',
        'BLE_REQUIRED',
        'CAMPUS_NETWORK_NOT_DETECTED',
        'NOT_ENROLLED',
        'SERVER_UNREACHABLE',
      ];

      for (final code in errorCodes) {
        final errEn = stringsEn.getSafeError(code);
        final errFa = stringsFa.getSafeError(code);
        final errPs = stringsPs.getSafeError(code);

        expect(errEn['title'], isNotEmpty);
        expect(errEn['subtitle'], isNotEmpty);
        expect(errFa['title'], isNotEmpty);
        expect(errFa['subtitle'], isNotEmpty);
        expect(errPs['title'], isNotEmpty);
        expect(errPs['subtitle'], isNotEmpty);

        // Verify zero SQL, database column, or traceback leakage
        for (final msg in [errEn, errFa, errPs]) {
          final combined = '${msg['title']} ${msg['subtitle']}'.toLowerCase();
          expect(combined.contains('select '), isFalse);
          expect(combined.contains('table '), isFalse);
          expect(combined.contains('syntaxerror'), isFalse);
          expect(combined.contains('traceback'), isFalse);
          expect(combined.contains('psycopg'), isFalse);
        }
      }
    });
  });

  group('StudentHomeScreen Multilingual & RTL Widget Tests', () {
    testWidgets('Renders in Dari with RTL directionality and Afghan terms',
        (WidgetTester tester) async {
      final mockClient = ApiClient(baseUrl: 'http://localhost:8000');

      await tester.pumpWidget(
        MaterialApp(
          home: StudentHomeScreen(
            apiClient: mockClient,
            studentName: 'احمد فهیم',
            studentNumber: 'KBL-2023-CS-042',
            initialLanguage: AppLanguage.fa,
            initialPercentage: null,
            initialStatus: 'NOT_APPLICABLE',
          ),
        ),
      );

      // Verify Dari App Title
      expect(find.text('حاضری پوهنتون'), findsOneWidget);

      // Verify Dari Not Applicable standing
      expect(
          find.text('غیرقابل تطبیق (بدون جلسات واجد شرایط)'), findsOneWidget);

      // Verify Dari Quick Actions
      expect(find.text('اسکن کیو‌آر حاضری'), findsOneWidget);
      expect(find.text('اعتبار دستگاه'), findsOneWidget);
      expect(find.text('دفتر ثبت حاضری'), findsOneWidget);
      expect(find.text('صف همگام‌سازی آفلاین'), findsOneWidget);

      // Verify Dari Invariant Card Text
      expect(find.textContaining('ساعت رسمی سرور پوهنتون تنها مرجع معتبر است'),
          findsOneWidget);
    });

    testWidgets('Renders in Pashto with RTL directionality and Afghan terms',
        (WidgetTester tester) async {
      final mockClient = ApiClient(baseUrl: 'http://localhost:8000');

      await tester.pumpWidget(
        MaterialApp(
          home: StudentHomeScreen(
            apiClient: mockClient,
            studentName: 'احمد فهیم',
            studentNumber: 'KBL-2023-CS-042',
            initialLanguage: AppLanguage.ps,
            initialPercentage: null,
            initialStatus: 'NOT_APPLICABLE',
          ),
        ),
      );

      // Verify Pashto App Title
      expect(find.text('د پوهنتون حاضري'), findsOneWidget);

      // Verify Pashto Not Applicable standing
      expect(find.text('د تطبیق وړ نه دی (د شرایطو وړ ناستې نشته)'),
          findsOneWidget);

      // Verify Pashto Quick Actions
      expect(find.text('د حاضرۍ کیو‌آر سکن'), findsOneWidget);
      expect(find.text('د آلې باور'), findsOneWidget);
      expect(find.text('د حاضرۍ کتابچه'), findsOneWidget);
      expect(find.text('آفلاین همغږۍ قطار'), findsOneWidget);

      // Verify Pashto Invariant Card Text
      expect(find.textContaining('یوازې د پوهنتون د سرور رسمي وخت باوري دی'),
          findsOneWidget);
    });

    testWidgets('Switching language interactively updates the UI dynamically',
        (WidgetTester tester) async {
      final mockClient = ApiClient(baseUrl: 'http://localhost:8000');

      await tester.pumpWidget(
        MaterialApp(
          home: StudentHomeScreen(
            apiClient: mockClient,
            studentName: 'Ahmad Fahim',
            studentNumber: 'KBL-2023-CS-042',
            initialLanguage: AppLanguage.en,
          ),
        ),
      );

      // Starts in English
      expect(find.text('University Attendance'), findsOneWidget);
      expect(find.text('Scan QR Check-In'), findsOneWidget);

      // Tap language switch icon in AppBar
      final langButton = find.byKey(const Key('language_toggle_btn'));
      expect(langButton, findsOneWidget);
      await tester.tap(langButton);
      await tester.pumpAndSettle();

      // Bottom sheet is visible with options
      expect(find.text('Select Language'), findsOneWidget);
      final faOption = find.byKey(const Key('lang_option_fa'));
      expect(faOption, findsOneWidget);

      // Select Dari
      await tester.tap(faOption);
      await tester.pumpAndSettle();

      // Verify UI is now in Dari
      expect(find.text('حاضری پوهنتون'), findsOneWidget);
      expect(find.text('اسکن کیو‌آر حاضری'), findsOneWidget);
      expect(find.text('Scan QR Check-In'), findsNothing);
    });
  });
}
