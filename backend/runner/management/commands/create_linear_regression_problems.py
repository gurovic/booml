from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from runner.models import Problem, ProblemDescriptor, ProblemData
from django.core.files.base import ContentFile
import pandas as pd
import numpy as np
import io

class Command(BaseCommand):
    help = 'Create linear regression problems'

    def handle(self, *args, **options):
        # Get or create an admin user to assign as author
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        
        # Define 5 different linear regression problems
        problems_data = [
            {
                'title': 'Simple Linear Regression: House Prices',
                'rating': 1000,
                'statement': '''# Simple Linear Regression: House Prices

Predict house prices based on the size of the house (square meters).

## Dataset Description
- Train: Contains 'size' (square meters) and 'price' (target variable)
- Test: Contains only 'size', predict corresponding 'price'
- Sample submission: Format for submission

## Task
Build a simple linear regression model to predict house prices based on house size.

Target column: `price`
ID column: `id`
Metric: RMSE (Root Mean Square Error)
'''
            },
            {
                'title': 'Multiple Linear Regression: Car Prices',
                'rating': 1200,
                'statement': '''# Multiple Linear Regression: Car Prices

Predict car prices based on multiple features.

## Dataset Description
- Train: Contains features like 'year', 'mileage', 'engine_size', 'fuel_type' and 'price' (target)
- Test: Contains features but no 'price', predict corresponding 'price'
- Sample submission: Format for submission

## Task
Build a multiple linear regression model to predict car prices based on multiple features.

Target column: `price`
ID column: `id`
Metric: RMSE (Root Mean Square Error)
'''
            },
            {
                'title': 'Polynomial Regression: Temperature Prediction',
                'rating': 1400,
                'statement': '''# Polynomial Regression: Temperature Prediction

Predict temperature based on day of year with polynomial relationship.

## Dataset Description
- Train: Contains 'day_of_year' and 'temperature' (target variable)
- Test: Contains only 'day_of_year', predict corresponding 'temperature'
- Sample submission: Format for submission

## Task
Build a polynomial regression model to predict temperature based on day of year. 
Consider quadratic or cubic relationships between day of year and temperature.

Target column: `temperature`
ID column: `id`
Metric: RMSE (Root Mean Square Error)
'''
            },
            {
                'title': 'Ridge Regression: Medical Costs',
                'rating': 1600,
                'statement': '''# Ridge Regression: Medical Costs

Predict medical insurance costs based on patient characteristics with regularization.

## Dataset Description
- Train: Contains features like 'age', 'bmi', 'children', 'smoker', 'region' and 'charges' (target)
- Test: Contains features but no 'charges', predict corresponding 'charges'
- Sample submission: Format for submission

## Task
Build a ridge regression model to predict medical insurance costs. 
Use regularization to prevent overfitting with multiple correlated features.

Target column: `charges`
ID column: `id`
Metric: RMSE (Root Mean Square Error)
'''
            },
            {
                'title': 'Lasso Regression: Sales Prediction',
                'rating': 1800,
                'statement': '''# Lasso Regression: Sales Prediction

Predict product sales based on advertising budgets with feature selection.

## Dataset Description
- Train: Contains 'tv_budget', 'radio_budget', 'newspaper_budget' and 'sales' (target)
- Test: Contains advertising budgets but no 'sales', predict corresponding 'sales'
- Sample submission: Format for submission

## Task
Build a lasso regression model to predict sales. 
Use L1 regularization for feature selection to identify most important advertising channels.

Target column: `sales`
ID column: `id`
Metric: RMSE (Root Mean Square Error)
'''
            }
        ]
        
        created_problems = []
        
        for problem_data in problems_data:
            # Create the problem
            problem = Problem.objects.create(
                title=problem_data['title'],
                statement=problem_data['statement'],
                rating=problem_data['rating'],
                author=admin_user,
                is_published=True
            )
            
            # Create the problem descriptor
            descriptor = ProblemDescriptor.objects.create(
                problem=problem,
                id_column='id',
                target_column=self.get_target_column(problem_data['title']),
                metric='rmse',
                id_type='int',
                target_type='float',
                check_order=False,
                metric_name='rmse'
            )
            
            # Create empty problem data (we'll add files later)
            problem_data_obj = ProblemData.objects.create(problem=problem)
            
            created_problems.append({
                'problem': problem,
                'descriptor': descriptor,
                'data': problem_data_obj
            })
            
            self.stdout.write(f"Created problem: {problem.title}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(created_problems)} linear regression problems!')
        )

    def get_target_column(self, title):
        """Extract target column name from problem title"""
        if 'House Prices' in title:
            return 'price'
        elif 'Car Prices' in title:
            return 'price'
        elif 'Temperature' in title:
            return 'temperature'
        elif 'Medical Costs' in title:
            return 'charges'
        elif 'Sales Prediction' in title:
            return 'sales'
        return 'target'