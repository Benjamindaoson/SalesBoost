import React from 'react';
import { Calendar, TrendingUp, CheckCircle, Clock } from 'lucide-react';

interface ProjectCardProps {
  project: {
    id: number;
    name: string;
    description: string;
    status: 'active' | 'completed' | 'archived';
    created_at: string;
    updated_at: string;
    tasks_count?: number;
    completed_tasks?: number;
    completion_rate?: number;
    total_sessions?: number;
    avg_score?: number;
  };
  onClick?: () => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({ project, onClick }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'completed':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'archived':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <Clock className="h-4 w-4" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      default:
        return <Calendar className="h-4 w-4" />;
    }
  };

  const completionRate = project.completion_rate || 0;
  const tasksCount = project.tasks_count || 0;
  const completedTasks = project.completed_tasks || 0;
  const totalSessions = project.total_sessions || 0;
  const avgScore = project.avg_score || 0;

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 cursor-pointer border border-gray-200 overflow-hidden"
    >
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">{project.name}</h3>
            <p className="text-sm text-gray-600 line-clamp-2">{project.description}</p>
          </div>
          <span
            className={`ml-4 px-3 py-1 inline-flex items-center text-xs font-semibold rounded-full border ${getStatusColor(
              project.status
            )}`}
          >
            {getStatusIcon(project.status)}
            <span className="ml-1 capitalize">{project.status}</span>
          </span>
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>Progress</span>
              <span className="font-medium">{completionRate.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${completionRate}%` }}
              ></div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center text-gray-600 mb-1">
                <CheckCircle className="h-4 w-4 mr-1" />
                <span className="text-xs">Tasks</span>
              </div>
              <p className="text-lg font-semibold text-gray-900">
                {completedTasks}/{tasksCount}
              </p>
            </div>

            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center text-gray-600 mb-1">
                <TrendingUp className="h-4 w-4 mr-1" />
                <span className="text-xs">Avg Score</span>
              </div>
              <p className="text-lg font-semibold text-gray-900">{avgScore.toFixed(1)}</p>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-200">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center">
                <Calendar className="h-3 w-3 mr-1" />
                <span>Created {new Date(project.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center">
                <Clock className="h-3 w-3 mr-1" />
                <span>{totalSessions} sessions</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
        <button className="text-sm font-medium text-blue-600 hover:text-blue-700">
          View Details →
        </button>
      </div>
    </div>
  );
};
