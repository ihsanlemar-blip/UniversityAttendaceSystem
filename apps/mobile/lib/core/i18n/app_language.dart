import 'package:flutter/material.dart';

/// Supported languages in the Digital Student Attendance System mobile client.
enum AppLanguage {
  en,
  fa,
  ps,
}

extension AppLanguageExtension on AppLanguage {
  /// ISO language code
  String get code {
    switch (this) {
      case AppLanguage.en:
        return 'en';
      case AppLanguage.fa:
        return 'fa';
      case AppLanguage.ps:
        return 'ps';
    }
  }

  /// Full locale including Afghan country code where applicable
  Locale get locale {
    switch (this) {
      case AppLanguage.en:
        return const Locale('en', 'US');
      case AppLanguage.fa:
        return const Locale('fa', 'AF');
      case AppLanguage.ps:
        return const Locale('ps', 'AF');
    }
  }

  /// Native display name for language selection UI
  String get displayName {
    switch (this) {
      case AppLanguage.en:
        return 'English';
      case AppLanguage.fa:
        return 'دری (Dari)';
      case AppLanguage.ps:
        return 'پښتو (Pashto)';
    }
  }

  /// Directionality: Dari and Pashto are authentic right-to-left scripts
  bool get isRtl {
    switch (this) {
      case AppLanguage.en:
        return false;
      case AppLanguage.fa:
      case AppLanguage.ps:
        return true;
    }
  }

  TextDirection get textDirection =>
      isRtl ? TextDirection.rtl : TextDirection.ltr;
}
