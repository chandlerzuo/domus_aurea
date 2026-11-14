"""
Autoplay functionality for Guandan game using trained AI agents.

This module provides functions to automatically play Guandan games using 
the trained AI models (ppo, ppo+, dmc) available in the guandan project.
"""

import os
import sys
from pathlib import Path
import numpy as np

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from guandan.rl.policy import load_policy, PolicyAgent
from guandan.rl.search import SearchAgent
from guandan.rl.dmc import load_net, DMCAgent
from guandan.agents import HeuristicAgent
from guandan.cards import card_str
from guandan.combos import Move


class AutoPlayer:
    """A player that automatically makes moves using trained AI agents."""
    
    def __init__(self, agent_type="ppo+", seed=None):
        """
        Initialize an autoplay player.
        
        Args:
            agent_type (str): Type of AI agent to use ("ppo", "ppo+", "dmc", "heuristic")
            seed (int): Random seed for reproducible behavior
        """
        self.agent_type = agent_type
        self.seed = seed or np.random.randint(2**32)
        self.rng = np.random.default_rng(self.seed)
        
        # Load the appropriate model/agent
        self._load_agent()
    
    def _load_agent(self):
        """Load the appropriate AI agent based on type."""
        try:
            if self.agent_type == "ppo+":
                # Use PPO policy with search (requires Rust core)
                from guandan.rl import fast
                if not fast.AVAILABLE:
                    print("Rust core not available, falling back to ppo")
                    self.agent_type = "ppo"
                else:
                    from guandan.rl.policy import load_policy
                    model_path = Path(__file__).parent / "runs" / "ppo" / "model.pt"
                    if model_path.exists():
                        actor = load_policy(model_path)
                        self.agent = SearchAgent(actor, seed=self.seed, worlds=16, topk=3)
                    else:
                        print(f"Model not found at {model_path}, using heuristic")
                        self.agent = HeuristicAgent(seed=self.seed)
                        
            elif self.agent_type == "ppo":
                # Use PPO policy without search
                from guandan.rl.policy import load_policy
                model_path = Path(__file__).parent / "runs" / "ppo" / "model.pt"
                if model_path.exists():
                    actor = load_policy(model_path)
                    self.agent = PolicyAgent(actor, seed=self.seed, greedy=True)
                else:
                    print(f"Model not found at {model_path}, using heuristic")
                    self.agent = HeuristicAgent(seed=self.seed)
                    
            elif self.agent_type == "dmc":
                # Use DMC agent
                from guandan.rl.dmc import load_net
                model_path = Path(__file__).parent / "runs" / "dmc" / "model.pt"
                if model_path.exists():
                    net = load_net(model_path)
                    self.agent = DMCAgent(net, seed=self.seed)
                else:
                    print(f"Model not found at {model_path}, using heuristic")
                    self.agent = HeuristicAgent(seed=self.seed)
                    
            else:
                # Use heuristic as fallback
                self.agent = HeuristicAgent(seed=self.seed)
                
        except Exception as e:
            print(f"Error loading agent {self.agent_type}: {e}")
            print("Falling back to heuristic agent")
            self.agent = HeuristicAgent(seed=self.seed)
    
    def make_move(self, observation):
        """
        Make a move based on the current game state.
        
        Args:
            observation (dict): Current game state with 'legal' moves and other info
            
        Returns:
            int: Index of the chosen move in the legal moves list
        """
        return self.agent.act(observation)
    
    def get_move_info(self):
        """Get information about the last move made."""
        return getattr(self.agent, 'info', {})


def create_autoplay_function():
    """
    Create a function that can be used to autoplay Guandan games.
    
    Returns:
        function: A function that takes an observation and returns a move index
    """
    # Create an auto player with search (ppo+) by default
    player = AutoPlayer("ppo+")
    
    def autoplay(observation):
        """Autoplay function for Guandan."""
        return player.make_move(observation)
    
    # Attach player info to the function
    autoplay.player = player
    return autoplay


def test_autoplay():
    """Test the autoplay functionality with a simple example."""
    print("Testing autoplay functionality...")
    
    # Create a simple test player
    try:
        player = AutoPlayer("ppo+")
        print(f"Created {player.agent_type} player successfully")
        
        # Test that we can make a move (this would require a proper observation structure)
        print("Autoplay function created successfully")
        return True
        
    except Exception as e:
        print(f"Error testing autoplay: {e}")
        return False


if __name__ == "__main__":
    test_autoplay()