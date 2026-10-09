import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/services/transparency_service.dart';

class PublicTransparencyDashboardScreen extends StatefulWidget {
  const PublicTransparencyDashboardScreen({super.key});

  @override
  State<PublicTransparencyDashboardScreen> createState() => _PublicTransparencyDashboardScreenState();
}

class _PublicTransparencyDashboardScreenState extends State<PublicTransparencyDashboardScreen> {
  final _transparencyService = TransparencyService();
  bool _isLoading = true;
  String? _selectedWard;

  Map<String, dynamic>? _stats;
  Map<String, dynamic>? _healthScore;

  final List<String> _wards = [
    'Aundh-Baner',
    'Bhavani Peth',
    'Bibwewadi',
    'Dhole Patil Road',
    'Ghole Road',
    'Hadapsar',
    'Kasba-Vishrambaugwada',
    'Kondhwa-Yewalewadi',
    'Kothrud-Bavdhan',
    'Nagar Road-Wadgaon Sheri',
    'Sahakarnagar',
    'Sinhagad Road',
    'Tilak Road',
    'Warje-Karvenagar',
    'Yerawada-Kalas-Dhanori',
  ];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        _transparencyService.getTransparencyStats(ward: _selectedWard),
        _transparencyService.getCivicHealthScore(ward: _selectedWard),
      ]);
      setState(() {
        _stats = results[0];
        _healthScore = results[1];
        _isLoading = false;
      });
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Public Transparency Dashboard', style: TextStyle(fontSize: 18)),
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
            child: DropdownButtonFormField<String>(
              value: _selectedWard,
              decoration: const InputDecoration(labelText: 'Filter by Ward (Area Intelligence)', border: OutlineInputBorder()),
              items: [
                const DropdownMenuItem(value: null, child: Text('All Wards (Overall)')),
                ..._wards.map((w) => DropdownMenuItem(value: w, child: Text(w))),
              ],
              onChanged: (val) {
                setState(() => _selectedWard = val);
                _loadData();
              },
            ),
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : RefreshIndicator(
                    onRefresh: _loadData,
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          if (_healthScore != null) _buildHealthScoreCard(_healthScore!),
                          const SizedBox(height: 24),
                          if (_stats != null) _buildStatsGrid(_stats!),
                          const SizedBox(height: 24),
                          _buildOpenMapCard(),
                        ],
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildHealthScoreCard(Map<String, dynamic> data) {
    final score = (data['overall_score'] as num).toDouble();
    final rating = data['rating'] as String;
    final components = data['components'] as Map<String, dynamic>;

    Color scoreColor = Colors.green;
    if (score < 50) scoreColor = Colors.red;
    else if (score < 75) scoreColor = Colors.orange;

    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Civic Health Score', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
            const SizedBox(height: 4),
            Text(
              _selectedWard == null ? 'Overall Platform Score' : '$_selectedWard Area Score',
              style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),
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
                        Text('${score.toInt()}', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: scoreColor)),
                        const Text('/ 100', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                      ],
                    ),
                  ],
                ),
                const SizedBox(width: 24),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(rating, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: scoreColor)),
                      const SizedBox(height: 8),
                      Text(
                        'Analyzed ${data['total_issues_analyzed']} civic issues to generate this explainable score.',
                        style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            const Text('Component Breakdown', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
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
                        child: Text(e.key.replaceAll('_', ' '), style: const TextStyle(fontSize: 13)),
                      ),
                    ),
                    Text('${(val['score'] as num).toStringAsFixed(1)} / ${val['weight']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsGrid(Map<String, dynamic> stats) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Key Metrics', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
        const SizedBox(height: 12),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.5,
          children: [
            _buildStatCard('Unique Issues', stats['total_unique_civic_issues'], Icons.tag, Colors.indigo),
            _buildStatCard('Resolved', stats['resolved_issues'], Icons.check_circle, Colors.green),
            _buildStatCard('In Progress', stats['in_progress_issues'], Icons.engineering, Colors.orange),
            _buildStatCard('Avg Resolution Time', '${(stats['average_resolution_hours'] as num?)?.toStringAsFixed(1) ?? 'N/A'} hrs', Icons.timer, Colors.blue),
          ],
        ),
      ],
    );
  }

  Widget _buildStatCard(String title, dynamic value, IconData icon, Color color) {
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
              Expanded(child: Text(title, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary))),
            ],
          ),
          const SizedBox(height: 8),
          Text('$value', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color)),
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
              decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(12)),
              child: const Icon(Icons.map, color: Colors.white),
            ),
            const SizedBox(width: 16),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Public Civic Map', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.primaryDark)),
                  Text('View all reported issues and resolution status visually on the map.', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
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
