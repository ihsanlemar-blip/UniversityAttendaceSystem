import 'app_language.dart';
import 'translations_en.dart';
import 'translations_fa.dart';
import 'translations_ps.dart';

/// Centralized strings and safe error mapping utility for DSAS mobile client.
class AppStrings {
  final AppLanguage language;

  const AppStrings(this.language);

  static const Map<AppLanguage, Map<String, String>> _dictionaries = {
    AppLanguage.en: translationsEn,
    AppLanguage.fa: translationsFa,
    AppLanguage.ps: translationsPs,
  };

  /// Retrieve an instance for a given AppLanguage
  static AppStrings get(AppLanguage lang) => AppStrings(lang);

  /// Retrieve localized string by key with English fallback
  String t(String key) {
    final dict = _dictionaries[language] ?? translationsEn;
    return dict[key] ?? translationsEn[key] ?? key;
  }

  /// Safe, localized error message resolver mapping backend error codes to user-facing messages.
  /// Strictly prevents internal server or SQL details from leaking to the student screen.
  Map<String, String> getSafeError(String? errorCode) {
    switch (errorCode) {
      case 'TOKEN_EXPIRED':
        return {
          'title': t('token_expired_title'),
          'subtitle': t('token_expired_subtitle'),
        };
      case 'CHECKPOINT_NOT_OPEN':
        return {
          'title': t('checkpoint_not_open_title'),
          'subtitle': t('checkpoint_not_open_subtitle'),
        };
      case 'SESSION_CLOSED':
        return {
          'title': t('session_closed_title'),
          'subtitle': t('session_closed_subtitle'),
        };
      case 'DEVICE_NOT_REGISTERED':
        return {
          'title': t('device_not_registered_title'),
          'subtitle': t('device_not_registered_subtitle'),
        };
      case 'BLE_REQUIRED':
        return {
          'title': t('ble_required_title'),
          'subtitle': t('ble_required_subtitle'),
        };
      case 'CAMPUS_NETWORK_NOT_DETECTED':
        return {
          'title': t('campus_wifi_required_title'),
          'subtitle': t('campus_wifi_required_subtitle'),
        };
      case 'NOT_ENROLLED':
        return {
          'title': t('not_enrolled_title'),
          'subtitle': t('not_enrolled_subtitle'),
        };
      case 'SERVER_UNREACHABLE':
        return {
          'title': t('server_unreachable_title'),
          'subtitle': t('server_unreachable_subtitle'),
        };
      default:
        return {
          'title': t('server_unreachable_title'),
          'subtitle': t('server_unreachable_subtitle'),
        };
    }
  }
}
