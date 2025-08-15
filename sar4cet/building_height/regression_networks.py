import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import joblib

class BoundingBoxRegressor(nn.Module):
    """
    Neural network for building height estimation from SAR image features.
    
    Based on bounding box regression methodology for building height retrieval
    from single SAR imagery.
    """
    
    def __init__(self, input_features=20, hidden_layers=[128, 64, 32]):
        """
        Initialize the bounding box regressor network.
        
        Parameters
        ----------
        input_features : int
            Number of input features extracted from SAR imagery
        hidden_layers : list
            List of hidden layer sizes
        """
        super(BoundingBoxRegressor, self).__init__()
        
        layers = []
        prev_size = input_features
        
        # Create hidden layers
        for hidden_size in hidden_layers:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_size = hidden_size
        
        # Output layer for height prediction
        layers.append(nn.Linear(prev_size, 1))
        
        self.network = nn.Sequential(*layers)
        
    def forward(self, x):
        """
        Forward pass through the network.
        
        Parameters
        ----------
        x : torch.Tensor
            Input features tensor
            
        Returns
        -------
        torch.Tensor
            Predicted building heights
        """
        return self.network(x)

def train_height_model(features, heights, model_type='neural_network', 
                      test_size=0.2, random_state=42, epochs=100, 
                      learning_rate=0.001, save_path=None):
    """
    Train a building height estimation model.
    
    Parameters
    ----------
    features : numpy.ndarray
        Feature matrix (n_samples, n_features)
    heights : numpy.ndarray
        Target heights (n_samples,)
    model_type : str
        Type of model to train ('neural_network' or 'random_forest')
    test_size : float
        Fraction of data to use for testing
    random_state : int
        Random seed for reproducibility
    epochs : int
        Number of training epochs (for neural network)
    learning_rate : float
        Learning rate (for neural network)
    save_path : str, optional
        Path to save the trained model
        
    Returns
    -------
    dict
        Dictionary containing trained model and performance metrics
    """
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        features, heights, test_size=test_size, random_state=random_state
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    if model_type == 'neural_network':
        # Train neural network
        model = BoundingBoxRegressor(input_features=features.shape[1])
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train_scaled)
        y_train_tensor = torch.FloatTensor(y_train.reshape(-1, 1))
        X_test_tensor = torch.FloatTensor(X_test_scaled)
        
        # Training loop
        model.train()
        train_losses = []
        
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = model(X_train_tensor)
            loss = criterion(outputs, y_train_tensor)
            loss.backward()
            optimizer.step()
            train_losses.append(loss.item())
            
            if (epoch + 1) % 20 == 0:
                print(f'Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}')
        
        # Evaluate
        model.eval()
        with torch.no_grad():
            y_pred = model(X_test_tensor).numpy().flatten()
            
    elif model_type == 'random_forest':
        # Train random forest
        model = RandomForestRegressor(
            n_estimators=100, 
            random_state=random_state,
            max_depth=10,
            min_samples_split=5
        )
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
        train_losses = None
        
    else:
        raise ValueError(f"Unknown model_type: {model_type}")
    
    # Calculate metrics
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Performance:")
    print(f"RMSE: {rmse:.2f} meters")
    print(f"R²: {r2:.3f}")
    
    # Save model if path provided
    if save_path:
        if model_type == 'neural_network':
            torch.save({
                'model_state_dict': model.state_dict(),
                'scaler': scaler,
                'model_config': {
                    'input_features': features.shape[1],
                    'hidden_layers': [128, 64, 32]
                }
            }, save_path)
        else:
            joblib.dump({
                'model': model,
                'scaler': scaler
            }, save_path)
        print(f"Model saved to {save_path}")
    
    return {
        'model': model,
        'scaler': scaler,
        'metrics': {
            'rmse': rmse,
            'r2': r2,
            'mse': mse
        },
        'predictions': {
            'y_test': y_test,
            'y_pred': y_pred
        },
        'train_losses': train_losses
    }

def load_trained_model(model_path, model_type='neural_network'):
    """
    Load a previously trained model.
    
    Parameters
    ----------
    model_path : str
        Path to the saved model
    model_type : str
        Type of model ('neural_network' or 'random_forest')
        
    Returns
    -------
    dict
        Dictionary containing model and scaler
    """
    if model_type == 'neural_network':
        checkpoint = torch.load(model_path)
        model = BoundingBoxRegressor(**checkpoint['model_config'])
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        scaler = checkpoint['scaler']
    else:
        checkpoint = joblib.load(model_path)
        model = checkpoint['model']
        scaler = checkpoint['scaler']
    
    return {
        'model': model,
        'scaler': scaler
    }

def predict_building_heights(model_data, features):
    """
    Predict building heights using a trained model.
    
    Parameters
    ----------
    model_data : dict
        Dictionary containing model and scaler from load_trained_model
    features : numpy.ndarray
        Feature matrix for prediction
        
    Returns
    -------
    numpy.ndarray
        Predicted heights
    """
    model = model_data['model']
    scaler = model_data['scaler']
    
    # Scale features
    features_scaled = scaler.transform(features)
    
    if isinstance(model, BoundingBoxRegressor):
        # Neural network prediction
        model.eval()
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features_scaled)
            predictions = model(features_tensor).numpy().flatten()
    else:
        # Random forest prediction
        predictions = model.predict(features_scaled)
    
    return predictions