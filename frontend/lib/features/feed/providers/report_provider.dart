import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/services/report_service.dart';
import '../../../shared/models/report_model.dart';

class ReportListState {
  final bool isLoading;
  final List<ReportModel> reports;
  final List<ReportModel> myReports;
  final String? selectedCategory;
  final String? selectedStatus;
  final String? errorMessage;

  ReportListState({
    this.isLoading = false,
    this.reports = const [],
    this.myReports = const [],
    this.selectedCategory,
    this.selectedStatus,
    this.errorMessage,
  });

  ReportListState copyWith({
    bool? isLoading,
    List<ReportModel>? reports,
    List<ReportModel>? myReports,
    String? selectedCategory,
    String? selectedStatus,
    String? errorMessage,
    bool clearSelectedCategory = false,
    bool clearSelectedStatus = false,
  }) {
    return ReportListState(
      isLoading: isLoading ?? this.isLoading,
      reports: reports ?? this.reports,
      myReports: myReports ?? this.myReports,
      selectedCategory: clearSelectedCategory ? null : selectedCategory ?? this.selectedCategory,
      selectedStatus: clearSelectedStatus ? null : selectedStatus ?? this.selectedStatus,
      errorMessage: errorMessage,
    );
  }
}

class ReportListNotifier extends StateNotifier<ReportListState> {
  final ReportService _reportService = ReportService();
  String? _activeSearchQuery;

  ReportListNotifier() : super(ReportListState()) {
    fetchReports();
  }

  Future<void> fetchReports() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final reports = _activeSearchQuery == null
          ? await _reportService.getReports(
              category: state.selectedCategory,
              status: state.selectedStatus,
            )
          : await _reportService.searchReports(
              query: _activeSearchQuery!,
              category: state.selectedCategory,
              status: state.selectedStatus,
            );
      state = state.copyWith(isLoading: false, reports: reports);
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  Future<void> searchReports(String query) async {
    final normalized = query.trim();
    _activeSearchQuery = normalized.length >= 2 ? normalized : null;
    await fetchReports();
  }

  Future<void> fetchMyReports() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final myReports = await _reportService.getReports(myReports: true);
      state = state.copyWith(isLoading: false, myReports: myReports);
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  void filterCategory(String? category) {
    if (state.selectedCategory == category) {
      state = state.copyWith(clearSelectedCategory: true);
    } else {
      state = state.copyWith(selectedCategory: category);
    }
    fetchReports();
  }

  void filterStatus(String? status) {
    if (state.selectedStatus == status) {
      state = state.copyWith(clearSelectedStatus: true);
    } else {
      state = state.copyWith(selectedStatus: status);
    }
    fetchReports();
  }

  Future<void> toggleUpvote(int reportId) async {
    try {
      final res = await _reportService.toggleUpvote(reportId);
      final hasUpvoted = res['has_upvoted'] as bool? ?? false;
      final totalUpvotes = res['total_upvotes'] as int? ?? 0;

      // Update in reports list
      final updatedReports = state.reports.map((r) {
        if (r.id == reportId) {
          r.hasUpvoted = hasUpvoted;
          r.upvotesCount = totalUpvotes;
        }
        return r;
      }).toList();

      state = state.copyWith(reports: updatedReports);
    } catch (_) {}
  }
}

final reportListProvider = StateNotifierProvider<ReportListNotifier, ReportListState>((ref) {
  return ReportListNotifier();
});
