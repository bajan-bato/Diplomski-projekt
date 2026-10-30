using System;
using System.Collections.Generic;

namespace backend.Models;

public partial class Review
{
    public int Status { get; set; }

    public int Issueid { get; set; }

    public int Analysisid { get; set; }

    public virtual Analysis Analysis { get; set; } = null!;

    public virtual Issue Issue { get; set; } = null!;
}
