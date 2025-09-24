import React, { useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Switch,
  FormControlLabel,
  Typography,
  Alert,
  CircularProgress,
  Tooltip
} from '@mui/material';
import {
  LocationOn,
  LocationOff,
  MyLocation,
  Refresh,
  Close
} from '@mui/icons-material';
import { useLocation } from '@/contexts/LocationContext';

interface LocationControlProps {
  showInSearch?: boolean;
  compact?: boolean;
}

const LocationControl: React.FC<LocationControlProps> = ({ 
  showInSearch = false, 
  compact = false 
}) => {
  const {
    locationData,
    isLoading,
    error,
    hasPermission,
    isLocationEnabled,
    requestLocation,
    clearLocation,
    setLocationEnabled,
    refreshLocation
  } = useLocation();

  const [settingsOpen, setSettingsOpen] = useState(false);

  const handleLocationToggle = async () => {
    if (!isLocationEnabled) {
      setLocationEnabled(true);
      if (hasPermission !== false) {
        await requestLocation();
      }
    } else {
      setLocationEnabled(false);
    }
  };

  const getLocationDisplay = () => {
    if (!locationData) return null;
    
    if (locationData.city && locationData.region) {
      return `${locationData.city}, ${locationData.region}`;
    } else if (locationData.city) {
      return locationData.city;
    } else if (locationData.region) {
      return locationData.region;
    } else {
      return `${locationData.latitude.toFixed(2)}, ${locationData.longitude.toFixed(2)}`;
    }
  };

  const LocationChip = () => {
    if (!isLocationEnabled) {
      return (
        <Chip
          icon={<LocationOff />}
          label="Location Off"
          variant="outlined"
          size="small"
          onClick={() => setSettingsOpen(true)}
        />
      );
    }

    if (isLoading) {
      return (
        <Chip
          icon={<CircularProgress size={16} />}
          label="Getting Location..."
          variant="outlined"
          size="small"
        />
      );
    }

    if (error) {
      return (
        <Chip
          icon={<LocationOff />}
          label="Location Error"
          color="error"
          variant="outlined"
          size="small"
          onClick={() => setSettingsOpen(true)}
        />
      );
    }

    if (locationData) {
      return (
        <Chip
          icon={<LocationOn />}
          label={getLocationDisplay()}
          color="primary"
          variant="outlined"
          size="small"
          onClick={() => setSettingsOpen(true)}
          onDelete={compact ? undefined : clearLocation}
        />
      );
    }

    // isLocationEnabled is true but no locationData yet - need to request location
    if (isLocationEnabled) {
      return (
        <Chip
          icon={<MyLocation />}
          label="Request Location"
          variant="outlined"
          size="small"
          onClick={handleLocationToggle}
        />
      );
    }

    // Fallback - location not enabled
    return (
      <Chip
        icon={<MyLocation />}
        label="Enable Location"
        variant="outlined"
        size="small"
        onClick={handleLocationToggle}
      />
    );
  };

  if (compact) {
    return (
      <>
        <LocationChip />
        <LocationSettingsDialog 
          open={settingsOpen} 
          onClose={() => setSettingsOpen(false)} 
        />
      </>
    );
  }

  return (
    <Box display="flex" alignItems="center" gap={1}>
      {showInSearch && (
        <Typography variant="body2" color="text.secondary">
          Location:
        </Typography>
      )}
      
      <LocationChip />
      
      {isLocationEnabled && locationData && (
        <Tooltip title="Refresh location">
          <IconButton 
            size="small" 
            onClick={refreshLocation}
            disabled={isLoading}
          >
            <Refresh />
          </IconButton>
        </Tooltip>
      )}

      <LocationSettingsDialog 
        open={settingsOpen} 
        onClose={() => setSettingsOpen(false)} 
      />
    </Box>
  );
};

interface LocationSettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

const LocationSettingsDialog: React.FC<LocationSettingsDialogProps> = ({ open, onClose }) => {
  const {
    locationData,
    isLoading,
    error,
    hasPermission,
    isLocationEnabled,
    requestLocation,
    clearLocation,
    setLocationEnabled,
    refreshLocation
  } = useLocation();

  const handleEnableLocation = async () => {
    setLocationEnabled(true);
    await requestLocation();
  };

  const handleDisableLocation = () => {
    setLocationEnabled(false);
    clearLocation();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            <LocationOn />
            Location Settings
          </Box>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Box display="flex" flexDirection="column" gap={2}>
          <FormControlLabel
            control={
              <Switch
                checked={isLocationEnabled}
                onChange={(e) => setLocationEnabled(e.target.checked)}
              />
            }
            label="Use my location for search"
          />

          <Typography variant="body2" color="text.secondary">
            Enable location to get more relevant search results for "near me" queries. 
            Your location is only used for search and is not stored on our servers.
          </Typography>

          {error && (
            <Alert severity="error">
              {error}
              {hasPermission === false && (
                <Box mt={1}>
                  <Typography variant="body2">
                    Please allow location access in your browser settings and try again.
                  </Typography>
                </Box>
              )}
            </Alert>
          )}

          {isLocationEnabled && locationData && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Current Location:
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {locationData.city && `${locationData.city}, `}
                {locationData.region && `${locationData.region}, `}
                {locationData.country}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Last updated: {new Date(locationData.timestamp).toLocaleString()}
              </Typography>
            </Box>
          )}

          {isLocationEnabled && !locationData && !isLoading && !error && (
            <Alert severity="info">
              Click "Request Location" to detect your current location.
            </Alert>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Close
        </Button>
        
        {isLocationEnabled && (
          <>
            {locationData && (
              <Button 
                onClick={refreshLocation} 
                disabled={isLoading}
                startIcon={isLoading ? <CircularProgress size={16} /> : <Refresh />}
              >
                Refresh
              </Button>
            )}
            
            {!locationData && !error && (
              <Button 
                onClick={requestLocation} 
                disabled={isLoading}
                variant="contained"
                startIcon={isLoading ? <CircularProgress size={16} /> : <MyLocation />}
              >
                Request Location
              </Button>
            )}
            
            <Button onClick={handleDisableLocation} color="error">
              Disable Location
            </Button>
          </>
        )}

        {!isLocationEnabled && (
          <Button 
            onClick={handleEnableLocation} 
            variant="contained"
            startIcon={<LocationOn />}
          >
            Enable Location
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default LocationControl;