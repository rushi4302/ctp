import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/services/transparency_service.dart';
import '../../../shared/utils/complaint_presentation.dart';

class PublicTransparencyDashboardScreen extends StatefulWidget {
  const PublicTransparencyDashboardScreen({
    super.key,
    this.transparencyService,
  });

  final TransparencyService? transparencyService;

  @override
  State<PublicTransparencyDashboardScreen> createState() =>
      _PublicTransparencyDashboardScreenState();
}

class _PublicTransparencyDashboardScreenState
    extends State<PublicTransparencyDashboardScreen> {
  late final TransparencyService _transparencyService;
  bool _isLoading = true;
  String? _loadError;
  String? _selectedLocality;

  Map<String, dynamic>? _allStats;
  Map<String, dynamic>? _healthScore;
  Map<String, Map<String, dynamic>> _localityData = {};
  List<String> _localities = [];

  @override
  void initState() {
    super.initState();
    _transparencyService = widget.transparencyService ?? TransparencyService();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final results = await Future.wait([
        _transparencyService.getTransparencyStats(),
        _transparencyService.getCivicHealthScore(),
      ]);
      final allStats = results[0];
      final localityDistribution = allStats['locality_distribution'];
      final localities = localityDistribution is Map
          ? (localityDistribution.keys
                .map((key) => key.toString())
                .where((name) => name.trim().isNotEmpty)
                .toList()
              ..sort())
          : <String>[];
      final localityResults = await Future.wait(
        localities.map((locality) async {
          final scopedResults = await Future.wait([
            _transparencyService.getTransparencyStats(locality: locality),
            _transparencyService.getCivicHealthScore(locality: locality),
          ]);
          return MapEntry(locality, {
            'stats': scopedResults[0],
            'score': scopedResults[1],
          });
        }),
      );
      setState(() {
        _allStats = allStats;
        _healthScore = results[1];
        _localities = localities;
        _localityData = Map.fromEntries(localityResults);
        _isLoading = false;
      });
    } catch (error) {
      setState(() {
        _loadError = error.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          'Public Transparency Dashboard',
          style: TextStyle(fontSize: 18),
        ),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.map),
            tooltip: 'View Public Map',
            onPressed: () => context.push('/map'),
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: Colors.white,
            child: DropdownButtonFormField<String?>(
              value: _selectedLocality,
              decoration: const InputDecoration(
                labelText: 'Filter by locality',
                border: OutlineInputBorder(),
              ),
              items: [
                const DropdownMenuItem<String?>(
                  value: null,
                  child: Text('All Localities (Overall)'),
                ),
                ..._localities.map(
                  (locality) => DropdownMenuItem<String?>(
                    value: locality,
                    child: Text(locality),
                  ),
                ),
              ],
              onChanged: (val) {
                setState(() => _selectedLocality = val);
              },
            ),
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _loadError != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(_loadError!, textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          FilledButton(
                            onPressed: _loadData,
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: _loadData,
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          if (_selectedLocality == null) ...[
                            if (_allStats != null)
                              _buildDataNotice(
                                _allStats!['data_notice'] as String?,
                              ),
                            if (_healthScore != null)
                              _buildHealthScoreCard(_healthScore!),
                            const SizedBox(height: 20),
                            _buildLocalityScores(),
                            const SizedBox(height: 24),
                            if (_allStats != null) _buildStatsGrid(_allStats!),
                          ] else if (_localityData[_selectedLocality]
                              case final locality?) ...[
                            _buildDataNotice(
                              (locality['stats']
                                      as Map<String, dynamic>)['data_notice']
                                  as String?,
                            ),
                            _buildHealthScoreCard(
                              locality['score'] as Map<String, dynamic>,
                            ),
                            const SizedBox(height: 20),
                            _buildLocalityScores(
                              selectedLocality: _selectedLocality,
                            ),
                            const SizedBox(height: 24),
                            _buildStatsGrid(
                              locality['stats'] as Map<String, dynamic>,
                            ),
                          ] else
                            const Center(
                              child: Text(
                                'No reliable locality data is available for this selection.',
                              ),
                            ),
                          if (_selectedLocality == null) ...[
                            const SizedBox(height: 24),
                            _buildOpenMapCard(),
                          ],
                        ],
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildDataNotice(String? notice) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        border: Border.all(color: Colors.amber.shade300),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        notice ??
            'Development/test data. These metrics are not official municipal statistics.',
        style: const TextStyle(fontSize: 12, color: AppColors.textPrimary),
      ),
    );
  }

  Widget _buildHealthScoreCard(Map<String, dynamic> data) {
    final scoreValue = data['overall_score'];
    final score = scoreValue is num ? scoreValue.toDouble() : null;
    final rating = humanizeStatus(data['rating'] as String);
    final components = data['components'] as Map<String, dynamic>;

    Color scoreColor = Colors.green;
    if (score == null) {
      scoreColor = Colors.blueGrey;
    } else if (score < 50) {
      scoreColor = Colors.red;
    } else if (score < 75) {
      scoreColor = Colors.orange;
    }

    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Civic Health Score',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _selectedLocality == null
                  ? 'Overall Platform Score'
                  : '$_selectedLocality Locality Score',
              style: const TextStyle(
                fontSize: 13,
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 16),
            if (score == null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.blueGrey.shade50,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      rating.replaceAll('_', ' '),
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: scoreColor,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      data['data_notice'] as String,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              )
            else
              Row(
                children: [
                  Stack(
                    alignment: Alignment.center,
                    children: [
                      SizedBox(
                        width: 100,
                        height: 100,
                        child: CircularProgressIndicator(
                          value: score / 100,
                          backgroundColor: Colors.grey.shade200,
                          color: scoreColor,
                          strokeWidth: 8,
                        ),
                      ),
                      Column(
                        children: [
                          Text(
                            '${score.toInt()}',
                            style: TextStyle(
                              fontSize: 32,
                              fontWeight: FontWeight.bold,
                              color: scoreColor,
                            ),
                          ),
                          const Text(
                            '/ 100',
                            style: TextStyle(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(width: 24),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          rating,
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: scoreColor,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Analyzed ${data['total_issues_analyzed']} civic issues to generate this explainable score.',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            if (score != null && components.isNotEmpty) ...[
              const SizedBox(height: 24),
              const Text(
                'Component Breakdown',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              const Divider(),
              ...components.entries.map((e) {
                final val = e.value as Map<String, dynamic>;
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Tooltip(
                          message: val['description'],
                          child: Text(
                            humanizeComponentName(e.key),
                            style: const TextStyle(fontSize: 13),
                          ),
                        ),
                      ),
                      Text(
                        (val['score'] as num).toStringAsFixed(1),
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildLocalityScores({String? selectedLocality}) {
    final allIssues =
        (_allStats?['total_unique_civic_issues'] as num?)?.toInt() ?? 0;
    final localityDistribution = _allStats?['locality_distribution'];
    final issuesWithLocality = localityDistribution is Map
        ? localityDistribution.values.fold<int>(
            0,
            (sum, value) => sum + ((value as num?)?.toInt() ?? 0),
          )
        : 0;
    final issuesWithoutLocality = allIssues - issuesWithLocality;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          selectedLocality == null
              ? 'Locality Health Scores'
              : 'Locality Score Details',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 10),
        const Padding(
          padding: EdgeInsets.only(bottom: 10),
          child: Text(
            'Counts use unique tracked issues; resolved includes closed issues. Resolution rate is separate from the Civic Health Score. Locality scores use the existing formula and require at least five issues.',
            style: TextStyle(
              fontSize: 12,
              height: 1.4,
              color: AppColors.textSecondary,
            ),
          ),
        ),
        if (issuesWithoutLocality > 0)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Text(
              '$issuesWithoutLocality tracked issues do not have a recorded locality and are excluded from locality scores.',
              style: const TextStyle(
                fontSize: 12,
                color: AppColors.textSecondary,
              ),
            ),
          ),
        if (_localityData.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: const Text(
              'Locality statistics are not available yet. Records without a reliable locality are excluded from locality scores.',
              style: TextStyle(
                fontSize: 13,
                height: 1.45,
                color: AppColors.textSecondary,
              ),
            ),
          )
        else
          ..._localityData.entries
              .where(
                (entry) =>
                    selectedLocality == null || entry.key == selectedLocality,
              )
              .map((entry) {
                final stats = entry.value['stats'] as Map<String, dynamic>;
                final scoreData = entry.value['score'] as Map<String, dynamic>;
                final total = (stats['total_unique_civic_issues'] as num)
                    .toInt();
                final reportTotal = (stats['total_valid_reports'] as num)
                    .toInt();
                final resolved =
                    ((stats['resolved_issues'] as num).toInt() +
                    (stats['closed_issues'] as num).toInt());
                final unresolved = total - resolved;
                final rate = (stats['resolution_rate'] as num).toDouble();
                final scoreValue = scoreData['overall_score'];
                final score = scoreValue is num ? scoreValue.toDouble() : null;
                final rating = humanizeStatus(
                  scoreData['rating'] as String? ?? 'INSUFFICIENT_DATA',
                );
                final components = scoreData['components'] is Map
                    ? Map<String, dynamic>.from(scoreData['components'] as Map)
                    : <String, dynamic>{};

                return Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                    side: BorderSide(color: Colors.grey.shade200),
                  ),
                  child: Column(
                    children: [
                      ListTile(
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 6,
                        ),
                        leading: const CircleAvatar(
                          backgroundColor: Color(0xFFE8F3F1),
                          child: Icon(
                            Icons.place_outlined,
                            color: AppColors.primary,
                          ),
                        ),
                        title: Text(
                          entry.key,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        subtitle: Padding(
                          padding: const EdgeInsets.only(top: 5),
                          child: Text(
                            '$reportTotal reports • $total unique issues • $resolved resolved (including closed) • $unresolved unresolved • ${rate.toStringAsFixed(1)}% resolution rate',
                          ),
                        ),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              score == null ? '—' : score.toStringAsFixed(1),
                              style: const TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: AppColors.primary,
                              ),
                            ),
                            Text(
                              rating,
                              style: const TextStyle(
                                fontSize: 10,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (score == null)
                        Padding(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
                          child: Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              scoreData['data_notice'] as String? ??
                                  'More complaint data is needed before a reliable score can be calculated.',
                              style: const TextStyle(
                                fontSize: 12,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ),
                        )
                      else if (components.isNotEmpty)
                        ExpansionTile(
                          title: const Text('Score components'),
                          children: components.entries.map((component) {
                            final details = component.value as Map;
                            return ListTile(
                              dense: true,
                              title: Text(humanizeComponentName(component.key)),
                              subtitle: Text(
                                details['description'] as String? ?? '',
                              ),
                              trailing: Text(
                                (details['score'] as num).toStringAsFixed(1),
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                    ],
                  ),
                );
              }),
      ],
    );
  }

  Widget _buildStatsGrid(Map<String, dynamic> stats) {
    final resolvedAndClosed =
        ((stats['resolved_issues'] as num?)?.toInt() ?? 0) +
        ((stats['closed_issues'] as num?)?.toInt() ?? 0);
    final rawLocalities = stats['locality_distribution'];
    final localityCounts = rawLocalities is Map
        ? rawLocalities.entries
              .map(
                (entry) => MapEntry(
                  entry.key.toString(),
                  (entry.value as num).toInt(),
                ),
              )
              .toList()
        : <MapEntry<String, int>>[];
    localityCounts.sort((a, b) => b.value.compareTo(a.value));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Key Metrics',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
        const SizedBox(height: 12),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.5,
          children: [
            _buildStatCard(
              'Unique Issues',
              stats['total_unique_civic_issues'],
              Icons.tag,
              Colors.indigo,
            ),
            _buildStatCard(
              'Pending',
              stats['pending_issues'],
              Icons.hourglass_top,
              Colors.deepOrange,
            ),
            _buildStatCard(
              'Assigned',
              stats['assigned_issues'],
              Icons.assignment_ind,
              Colors.blue,
            ),
            _buildStatCard(
              'Resolved / Closed',
              resolvedAndClosed,
              Icons.check_circle,
              Colors.green,
            ),
            _buildStatCard(
              'In Progress',
              stats['in_progress_issues'],
              Icons.engineering,
              Colors.orange,
            ),
            _buildStatCard(
              'Resolution Rate',
              '${stats['resolution_rate']}%',
              Icons.query_stats,
              Colors.teal,
            ),
            _buildStatCard(
              'Avg Resolution Time',
              '${(stats['average_resolution_hours'] as num?)?.toStringAsFixed(1) ?? 'N/A'} hrs',
              Icons.timer,
              Colors.blue,
            ),
          ],
        ),
        if (localityCounts.isNotEmpty) ...[
          const SizedBox(height: 20),
          const Text(
            'Issues by locality',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 6),
          ...localityCounts.map(
            (entry) => ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: const Icon(
                Icons.place_outlined,
                color: AppColors.primary,
              ),
              title: Text(entry.key),
              trailing: Text(
                '${entry.value}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildStatCard(
    String title,
    dynamic value,
    IconData icon,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '$value',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOpenMapCard() {
    return InkWell(
      onTap: () => context.push('/map'),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppColors.primary.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.primary.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.primary,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.map, color: Colors.white),
            ),
            const SizedBox(width: 16),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Public Civic Map',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: AppColors.primaryDark,
                    ),
                  ),
                  Text(
                    'View all reported issues and resolution status visually on the map.',
                    style: TextStyle(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.primary),
          ],
        ),
      ),
    );
  }
}
