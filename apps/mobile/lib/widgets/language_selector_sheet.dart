import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/i18n/app_language.dart';
import '../core/i18n/app_strings.dart';
import '../core/i18n/locale_provider.dart';

/// Shows an accessible modal bottom sheet for selecting the mobile interface language.
Future<void> showLanguageSelectorSheet(
    BuildContext context, WidgetRef ref) async {
  final currentLang = ref.read(appLanguageProvider);
  final strings = AppStrings.get(currentLang);

  await showModalBottomSheet<void>(
    context: context,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (BuildContext ctx) {
      return SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Semantics(
                header: true,
                child: Text(
                  strings.t('select_language'),
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1E293B),
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 16),
              ...AppLanguage.values.map((lang) {
                final isSelected = lang == currentLang;
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Directionality(
                    textDirection: lang.textDirection,
                    child: ListTile(
                      key: Key('lang_option_${lang.code}'),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: BorderSide(
                          color: isSelected
                              ? const Color(0xFF4F46E5)
                              : const Color(0xFFE2E8F0),
                          width: isSelected ? 2 : 1,
                        ),
                      ),
                      tileColor: isSelected
                          ? const Color(0xFFEEF2FF)
                          : Colors.transparent,
                      leading: Icon(
                        Icons.translate,
                        color: isSelected
                            ? const Color(0xFF4F46E5)
                            : const Color(0xFF64748B),
                      ),
                      title: Text(
                        lang.displayName,
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight:
                              isSelected ? FontWeight.bold : FontWeight.normal,
                          color: isSelected
                              ? const Color(0xFF312E81)
                              : const Color(0xFF1E293B),
                        ),
                      ),
                      trailing: isSelected
                          ? const Icon(
                              Icons.check_circle,
                              color: Color(0xFF4F46E5),
                            )
                          : null,
                      onTap: () {
                        ref
                            .read(appLanguageProvider.notifier)
                            .setLanguage(lang);
                        Navigator.of(ctx).pop();
                      },
                    ),
                  ),
                );
              }),
            ],
          ),
        ),
      );
    },
  );
}
