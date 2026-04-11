from app.models import Observation, Action, Reward
from tasks.tasks import get_task

class SQLAEnv:
    def __init__(self, task_id="task_easy"):
        self.task_data = get_task(task_id)
        self.current_step = 0
        self.findings = []
        self.done = False
        self.max_steps = 20 if task_id == "task_easy" else 30

    def reset(self, task_id="task_easy"):
        self.task_data = get_task(task_id)
        self.current_step = 0
        self.findings = []
        self.done = False
        return self._get_observation()

    def _get_observation(self):
        return Observation(
            task_id=self.task_data["id"],
            step=self.current_step,
            queries=self.task_data["queries"],
            schema=self.task_data["schema"],
            findings_so_far=self.findings,
            remaining_steps=self.max_steps - self.current_step,
            phase="auditing"
        )

    def step(self, action: Action):
        self.current_step += 1
        
        # Reward logic based on action type...
        score = 0.0
        feedback = "Action processed"
        
        if action.action_type == "submit_report":
            self.done = True
            score = self._evaluate_final_report()
            feedback = "Report submitted and evaluated."
        elif action.action_type == "scan_query":
            # Simple reward for identifying a real vulnerability
            if self.task_data["id"] == "task_easy" and action.query_index in self.task_data["vulnerabilities"]:
                score = 0.2
                feedback = "Correct vulnerability identified!"
            self.findings.append(action.dict())
        
        if self.current_step >= self.max_steps:
            self.done = True

        return self._get_observation(), Reward(value=score, message=feedback), self.done, {}

    def _evaluate_final_report(self):
        # Implementation of full evaluation logic here
        return 1.0 # Mock return for now
