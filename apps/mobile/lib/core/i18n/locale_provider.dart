import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'app_language.dart';

const String _kLanguageStorageKey = 'dsas_app_language';

/// StateNotifier managing mobile app language preference.
class LocaleNotifier extends StateNotifier<AppLanguage> {
  final FlutterSecureStorage _storage;

  LocaleNotifier(
      {FlutterSecureStorage? storage, AppLanguage initial = AppLanguage.en})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
              iOptions:
                  IOSOptions(accessibility: KeychainAccessibility.first_unlock),
            ),
        super(initial) {
    _loadSavedLanguage();
  }

  Future<void> _loadSavedLanguage() async {
    try {
      final saved = await _storage.read(key: _kLanguageStorageKey);
      if (saved != null) {
        if (saved == 'fa') {
          state = AppLanguage.fa;
        } else if (saved == 'ps') {
          state = AppLanguage.ps;
        } else {
          state = AppLanguage.en;
        }
      }
    } catch (_) {
      // Storage unavailable or in unit test
    }
  }

  Future<void> setLanguage(AppLanguage language) async {
    state = language;
    try {
      await _storage.write(key: _kLanguageStorageKey, value: language.code);
    } catch (_) {
      // Storage error ignored
    }
  }
}

final appLanguageProvider =
    StateNotifierProvider<LocaleNotifier, AppLanguage>((ref) {
  return LocaleNotifier();
});
