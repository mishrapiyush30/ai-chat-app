import React from 'react';
import { useChatContext } from '../context/ChatContext';

const MetricsBar: React.FC = () => {
  const { metrics } = useChatContext();

  if (!metrics) {
    return null;
  }

  return (
    <div className="bg-gray-50 border-t border-gray-200 py-2 px-4">
      <div className="flex justify-between text-xs text-gray-500">
        <div className="flex space-x-4">
          <div>
            <span className="font-medium">Tokens:</span>{' '}
            {metrics.totalTokens}
          </div>
          {metrics.latency && (
            <div>
              <span className="font-medium">Response time:</span>{' '}
              {metrics.latency.toFixed(2)}s
            </div>
          )}
        </div>
        <div>
          <span className="font-medium">Cost:</span>{' '}
          ${metrics.estimatedCost.toFixed(6)}
        </div>
      </div>
    </div>
  );
};

export default MetricsBar; 